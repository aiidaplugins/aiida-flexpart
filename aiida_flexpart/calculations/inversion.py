from aiida import common, engine, plugins

NetCDF = plugins.DataFactory("netcdf.data")

class InversionCalculation(engine.CalcJob):
    """AiiDA Inversion calculation plugin."""
    @classmethod
    def define(cls, spec):
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
        spec.input_namespace('netcdf_files', valid_type=NetCDF, required=True)

        #exit codes
        spec.outputs.dynamic = True
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):

        codeinfo = common.CodeInfo()
        codeinfo.cmdline_params = ['-p', 'params_inversion.yaml']
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        with folder.open('params_inversion.yaml', 'w') as f:
            paths = []
            for i,j in self.inputs.netcdf_files.items():
                paths.append(j.target_basepath)

        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['aiida.out','*.nc']

        return calcinfo
