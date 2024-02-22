# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_flexpart.
Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from aiida import orm, common, engine
import yaml

params_dict = {'rel.com':[],
                'domain.str': "EUROPE", 
                'nest': False,  
                'by.month': True,
                'overwrite': True,
                'nn.cores': 12,
                'debug': True,
                'compression': "lossy",
                'globals':{'title': "Total source sensitivities and boundary sensitivities from time-inversed LPDM simulations", 
                            'institution': "Empa, Duebendorf, Switzerland",
                            'author': "stephan.henne@empa.ch",
                            'model': "FLEXPART",
                            'model_version': "FLEXPART IFS (version 9.1_Empa)",
                            'met_model': "ECMWFHRES",
                            'species': "inert",
                            'LPDM_native_output_units': "s m3 kg-1",
                            'publication_acknowledgement': "Please acknowledge Empa in any publication that uses this data."
                            },
                'days':[],
                'path':[],
                'bs.path':[]
                }

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

        with folder.open('params.yaml', 'w') as f:
            rel,path,days =[],[],[]
            for i,j in self.inputs.remote.items():
                rel.append(i[10:])
                path.append(j.target_basepath)
                days.append(i[:10].replace("_", "-"))

            params_dict.update({'rel.com':list(set(rel)),
                                'path':path,
                                'days':days,
                                'bs.path':days
                                    })
            _ = yaml.dump(params_dict, f)

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = common.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = ['aiida.out','params.yaml']

        return calcinfo
