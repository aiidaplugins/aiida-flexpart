# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.
Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from aiida import orm, common, engine


class PostProcessingCalculation(engine.CalcJob):
    """AiiDA calculation plugin for post processing."""
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

        #INPUTS
        spec.input('metadata.options.parser_name', valid_type=str, default='flexpart.post')
        spec.input('input_dir', valid_type = orm.RemoteData, required=True,
                   help = 'main FLEXPART output dir')
        spec.input('input_offline_dir', valid_type = orm.RemoteData, required=False,
                   help = 'offline-nested FLEXPART output dir')
        spec.input('metadata.options.output_filename', valid_type=str, default='aiida.out', required=True)
        #exit codes
        spec.outputs.dynamic = True
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):

        params  = ['-m',self.inputs.input_dir.get_remote_path(),
                   '-r','./'
                  ]
        if 'input_offline_dir' in self.inputs:
            params += ['-n',self.inputs.input_offline_dir.get_remote_path()]

        codeinfo = common.CodeInfo()
        codeinfo.cmdline_params = params
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['grid_time_*.nc', 'boundary_sensitivity_*.nc', 'aiida.out']

        return calcinfo
