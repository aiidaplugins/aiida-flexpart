# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.
Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from pathlib import Path
from aiida import orm, common, engine
import yaml

with open(Path.home() / 'work/aiida-flexpart/config/params.yaml', 'r') as fp:
    params_dict = yaml.safe_load(fp)

cosmo_models = ['cosmo7', 'cosmo1', 'kenda1']
ECMWF_models = ['IFS_GL_05', 'IFS_GL_1', 'IFS_EU_02', 'IFS_EU_01']

class CollectSensCalculation(engine.CalcJob):
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

        #EXTRA INPUTS
        spec.input('model',valid_type = str,non_db=True, required = True)
        spec.input('outgrid',valid_type = str,non_db=True, required = True)
        spec.input('outgrid_n',valid_type = bool,non_db=True, required = True)

        #exit codes
        spec.outputs.dynamic = True
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):

        codeinfo = common.CodeInfo()
        codeinfo.cmdline_params = ['-p', 'params.yaml']
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        with folder.open('params.yaml', 'w') as f:
            rel,path,days =[],[],[]
            for i,j in self.inputs.remote.items():
                rel.append(i[10:])
                path.append(j.target_basepath)
                days.append(i[:10].replace('_', '-'))
                
            str_ = 'IFS'
            if self.inputs.model in cosmo_models:
                str_='COSMO'
            
            params_dict.update({'rel.com':list(set(rel)),
                                'path':path,
                                'days':days,
                                'bs.path':path,
                                'domain.str':self.inputs.outgrid,
                                'nest':self.inputs.outgrid_n,
                                'met_model':self.inputs.model,
                                'model_version':'FLEXPART '+str_
                                    })
            _ = yaml.dump(params_dict, f)

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['aiida.out','*.nc']

        return calcinfo
