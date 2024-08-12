# -*- coding: utf-8 -*-
from aiida import orm, common, engine
from aiida.plugins import DataFactory
import yaml

NetCDF = DataFactory('netcdf.data')


class Inversion(engine.CalcJob):
    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        #INPUTS metadata
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }
        spec.input('metadata.options.custom_scheduler_commands', valid_type=str, default='')
        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.input('metadata.options.output_filename', valid_type=str, default='aiida.out', required=True)
        #spec.input('metadata.options.parser_name', valid_type=str, default='collect.sens')

        #Inputs
        spec.input_namespace('remotes', valid_type = NetCDF, required=True)
        spec.input_namespace('observations', valid_type = NetCDF, required=True)

        spec.input('inv_params',valid_type = orm.Dict, required = True,
                   help = 'File containing inversion settings, either as R source file or yaml')
        spec.input('start_date',valid_type = orm.Str, required = True,
                   help = 'Start date (yyyy-mm-dd)')
        spec.input('end_date',valid_type = orm.Str, required = True,
                   help = 'End date (yyyy-mm-dd)')
        spec.input('chunk',valid_type = orm.Str, required = True,
                   help = "Options are 'year' and 'month'. Default is 'year'")
        spec.input('chunk_w',valid_type = orm.Str, required = True,
                   help = """Width of the individual inversion chunk. These can be wider than
			                 the chunking itself to allow for running average fluxes.,
                             Possible values are 'year' and '3year' for 'chunk.by=year' and,
                             'month' and '3month' for 'chunk.by=month'. Default is 'year'
                         """)

        #exit codes
        spec.outputs.dynamic = True

    def prepare_for_submission(self, folder):

        codeinfo = common.CodeInfo()
        codeinfo.cmdline_params = [
            '-f',
            'inversion_settings.yaml',
            '-s',
            self.inputs.start_date.value,
            '-e',
            self.inputs.end_date.value,
            '-c',
            self.inputs.chunk.value,
            '-w',
            self.inputs.chunk_w.value,
        ]
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        #create dict for yaml, add remotes by location
        remote_dict = {}
        for k,v in self.inputs.remotes.items():
             if k.split("-")[0] in remote_dict.keys():
                remote_dict[k.split("-")[0]].append(v.attributes["remote_path"]+'/'+k)
             else:
                remote_dict[k.split("-")[0]] = [v.attributes["remote_path"]+'/'+k]

        params_dict = self.inputs.inv_params.get_dict()
        for k,v in remote_dict.items():
            params_dict['sites'][k].update({'ft.fls':v})

        #replace _ by . in dict
        params_dict = {
    key.replace("_", "."): value for key, value in params_dict.items()
}

        with folder.open('inversion_settings.yaml', 'w') as f:
                _ = yaml.dump(params_dict, f)

        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['aiida.out']

        return calcinfo

