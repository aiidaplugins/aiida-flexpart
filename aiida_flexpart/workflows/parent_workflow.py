# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida_flexpart.workflows.child_meteo_workflow import TransferMeteoWorkflow
from aiida_flexpart.workflows.child_sim_workflow import FlexpartSimWorkflow



class ParentWorkflow(engine.WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)

        #extras
        spec.input('name', valid_type=str, non_db=True, required=False)

        spec.expose_inputs(TransferMeteoWorkflow)
        spec.expose_outputs(TransferMeteoWorkflow)
        spec.expose_inputs(FlexpartSimWorkflow)
        spec.expose_outputs(FlexpartSimWorkflow)
        spec.outputs.dynamic = True

        spec.outline(
            cls.setup,
            cls.transfer_meteo,
            cls.run_sim,
            cls.finalize,
        )

    def setup(self):
        #self.inputs.simulation_dates is orm.List
        self.ctx.month_chunks = 1
        if 'name' in self.inputs:
            out_n = 'None'
            if 'outgrid_nest' in self.inputs:
                out_n = self.inputs.outgrid_nest.get_dict()
            self.node.base.extras.set(
                self.inputs.name, {
                    'command': self.inputs.command.get_dict(),
                    'input_phy': self.inputs.input_phy.get_dict(),
                    'release': self.inputs.release_settings.get_dict(),
                    'locations': self.inputs.locations.get_dict(),
                    'integration_time': self.inputs.integration_time.value,
                    'offline_integration_time':
                    self.inputs.offline_integration_time.value,
                    'model': self.inputs.model,
                    'model_offline': self.inputs.model_offline,
                    'outgrid': self.inputs.outgrid.get_dict(),
                    'outgrid_nest': out_n
                })

    def transfer_meteo(self):
        child_1 = self.submit(TransferMeteoWorkflow,
                              **self.exposed_inputs(TransferMeteoWorkflow))
        return engine.ToContext(child_1=child_1)

    def run_sim(self):

        for i in range(len(self.inputs.simulation_dates)):
            child = self.submit(
                FlexpartSimWorkflow,
                **self.exposed_inputs(FlexpartSimWorkflow),
                date=orm.Str(self.inputs.simulation_dates[i]),
            )
            self.to_context(workchains=engine.append_(child))

    def finalize(self):
        self.out_many(
            self.exposed_outputs(self.ctx.child_1, TransferMeteoWorkflow))
        for w in self.ctx.workchains:
            self.out_many(self.exposed_outputs(w, FlexpartSimWorkflow))
