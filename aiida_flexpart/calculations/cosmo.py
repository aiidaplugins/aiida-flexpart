# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
import importlib
import pathlib
import jinja2
import datetime
import yaml

from aiida import orm
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.plugins import DataFactory
from aiida_flexpart.utils import convert_input_to_namelist_entry

class FlexpartCosmoCalculation(CalcJob):
    """AiiDA calculation plugin wrapping the FLEXPART executable."""

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # set default values for AiiDA options
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        spec.input('metadata.options.parser_name', valid_type=str, default='flexpart.cosmo')

        # new ports
        # Model settings namespace.
        spec.input_namespace('model_settings')
        spec.input('model_settings.release_settings', valid_type=orm.Dict, required=True)
        spec.input('model_settings.locations', valid_type=orm.Dict, required=True)
        spec.input('model_settings.command', valid_type=orm.Dict, required=True)
        spec.input('model_settings.input_phy',  valid_type=orm.Dict, required=True)
        
        spec.input('outgrid', valid_type=orm.Dict, help='Input file for the Lagrangian particle dispersion model FLEXPART.')
        spec.input('outgrid_nest', valid_type=orm.Dict, required=False, help='Input file for the Lagrangian particle dispersion model FLEXPART. Nested output grid.')
        spec.input('species', valid_type=orm.RemoteData, required=True)
        
        spec.input('metadata.options.output_filename', valid_type=str, default='aiida.out', required=True)
        spec.input_namespace('land_use', valid_type=orm.RemoteData, required=False, dynamic=True, help="#TODO")

        spec.output('output_file', valid_type=orm.SinglefileData, required=True, help="The output file of a calculation")
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')
        #spec.default_output_node = 'output_file'


    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """
        codeinfo = datastructures.CodeInfo()
        codeinfo.cmdline_params = [
            './', # Folder containing the inputs.
            './', # Folder containing the outputs.
            '/scratch/snx3000/yaa/FP2AiiDA/meteo/cosmo7/', # Large data input folder
            '/scratch/snx3000/yaa/FP2AiiDA/meteo/cosmo7/AVAILABLE', # File that lists all the individual input files that are available and assigns them a date
        ]
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]

        # Convert input_phy dictionary to the INPUT_PHY input file
        with folder.open('INPUT_PHY', 'w') as infile:
            infile.write('&parphy\n')
            for key, value in self.inputs.model_settings.input_phy.get_dict().items():
                infile.write(convert_input_to_namelist_entry(key, value))
            infile.write('/\n')
        
        
        # Dealing with simulation times.
        command_dict = self.inputs.model_settings.command.get_dict()
        simulation_beginning_date = datetime.datetime.strptime(command_dict.pop('simulation_date'),'%Y-%m-%d %H:%M:%S')
        age_class_time = datetime.timedelta(seconds=command_dict.pop('age_class'))
        release_chunk = datetime.timedelta(seconds=command_dict.pop('release_chunk'))
        release_duration = datetime.timedelta(seconds=command_dict.pop('release_duration'))
        release_beginning_date = simulation_beginning_date
        release_ending_date = simulation_beginning_date + release_duration * command_dict['simulation_direction']
        simulation_ending_date = release_ending_date + age_class_time * command_dict['simulation_direction']

        # FLEXPART requires the beginning date to be lower than the ending date.
        if simulation_beginning_date > simulation_ending_date:
            simulation_beginning_date, simulation_ending_date = simulation_ending_date, simulation_beginning_date
        if release_beginning_date > release_ending_date:
            release_beginning_date, release_ending_date = release_ending_date, release_beginning_date

        command_dict['simulation_beginning_date'] = [f'{simulation_beginning_date:%Y%m%d}', f'{simulation_beginning_date:%H%M%S}']
        command_dict['simulation_ending_date'] = [f'{simulation_ending_date:%Y%m%d}', f'{simulation_ending_date:%H%M%S}']

        # Dealing with locations.
        locations = self.inputs.model_settings.locations.get_dict()

        # Fill in the releases file.
        with folder.open('RELEASES', 'w') as infile:
            time_chunks = []
            current_time = release_beginning_date + release_chunk
            while current_time <= release_ending_date:
                time_chunks.append({
                    'begin': [f'{current_time-release_chunk:%Y%m%d}', f'{current_time-release_chunk:%H%M%S}'],
                    'end': [f'{current_time:%Y%m%d}', f'{current_time:%H%M%S}'],
                })
                current_time += release_chunk
            
            template = jinja2.Template(importlib.resources.read_text("aiida_flexpart.templates", "RELEASES.j2"))
            infile.write(template.render(
                time_chunks=time_chunks,
                locations=locations,
                release_settings=self.inputs.model_settings.release_settings.get_dict()
                )
            )

        # Fill in the AGECLASSES file.
        with folder.open('AGECLASSES', 'w') as infile:
            template = jinja2.Template(importlib.resources.read_text("aiida_flexpart.templates", "AGECLASSES.j2"))
            infile.write(template.render(age_class=int(age_class_time.total_seconds())))

        # Fill in the OUTGRID_NEST file if the corresponding dictionary is present.
        if 'outgrid_nest' in self.inputs:
            command_dict["nested_output"] = True
            with folder.open('OUTGRID_NEST', 'w') as infile:
                template = jinja2.Template(importlib.resources.read_text("aiida_flexpart.templates", "OUTGRID_NEST.j2"))
                infile.write(template.render(outgrid=self.inputs.outgrid_nest.get_dict()))
        else:
            command_dict["nested_output"] = False

        # Fill in the COMMAND file.
        with folder.open('COMMAND', 'w') as infile:
            template = jinja2.Template(importlib.resources.read_text("aiida_flexpart.templates", "COMMAND.j2"))
            infile.write(template.render(command=command_dict))
        
        # Fill in the OUTGRID file.
        with folder.open('OUTGRID', 'w') as infile:
            template = jinja2.Template(importlib.resources.read_text("aiida_flexpart.templates", "OUTGRID.j2"))
            infile.write(template.render(outgrid=self.inputs.outgrid.get_dict()))

        calcinfo.remote_symlink_list = []
        calcinfo.remote_symlink_list.append((self.inputs.species.computer.uuid, self.inputs.species.get_remote_path(), 'SPECIES'))

        # Dealing with land_use input namespace.
        for name, obj in self.inputs.land_use.items():
            computer_uuid = obj.computer.uuid
            file_path = obj.get_remote_path()
            file_name = file_path.split('/')[-1]
            calcinfo.remote_symlink_list.append((computer_uuid, file_path, file_name))

        calcinfo.retrieve_list = ['grid_time_*.nc', 'aiida.out']

        return calcinfo
