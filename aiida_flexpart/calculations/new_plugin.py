# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.
Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from aiida import orm, common, engine


class NewPluginCalculation(engine.CalcJob):
    """AiiDA calculation plugin."""
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

        #Inputs
        spec.input_namespace('remote', valid_type=orm.RemoteStashFolderData, required=True)

        #exit codes
        spec.outputs.dynamic = True
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):

        codeinfo = common.CodeInfo()
        codeinfo.cmdline_params = ['./','./']
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        with folder.open('file.csv','w') as f:
            for i,j in self.inputs.remote.items():
                f.write(f'{j.target_basepath}, {i}, date\n')

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['aiida.out']

        return calcinfo
