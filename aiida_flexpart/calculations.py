# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""

from aiida import orm
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.plugins import DataFactory

class FlexpartCalculation(CalcJob):
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
        spec.inputs['metadata']['options']['parser_name'].default = 'flexpart'

        # new ports
        spec.input('metadata.options.output_filename', valid_type=str, default='aiida.out')
        spec.input('outgrid', valid_type=orm.SinglefileData, help='Input file for the Lagrangian particle dispersion model FLEXPART.')
        spec.input('outgrid_nest', valid_type=orm.SinglefileData, help='Input file for the Lagrangian particle dispersion model FLEXPART. Nested output grid.')
        spec.input('releases', valid_type=orm.SinglefileData, help='Input file for the Lagrangian particle dispersion model FLEXPART.')
        spec.input('model_settings', valid_type=orm.SinglefileData, help='Command line parameters for diff')
        spec.input('age_classes', valid_type=orm.SinglefileData, help='Command line parameters for diff')

        spec.output('output_parameters', valid_type=orm.Dict, required=True, help="The results of a calculation")
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')
        spec.default_output_node = 'output_parameters'


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
        calcinfo.local_copy_list = [
            (self.inputs.outgrid.uuid, self.inputs.outgrid.filename, self.inputs.outgrid.filename),
            (self.inputs.outgrid_nest.uuid, self.inputs.outgrid_nest.filename, self.inputs.outgrid_nest.filename),
            (self.inputs.releases.uuid, self.inputs.releases.filename, self.inputs.releases.filename),
            (self.inputs.model_settings.uuid, self.inputs.model_settings.filename, self.inputs.model_settings.filename),
            (self.inputs.age_classes.uuid, self.inputs.age_classes.filename, self.inputs.age_classes.filename),

        ]
        calcinfo.retrieve_list = ['grid_time_*.nc']

        return calcinfo
