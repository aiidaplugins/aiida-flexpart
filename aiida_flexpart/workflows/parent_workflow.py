# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, orm
from aiida_flexpart.workflows.child_meteo_workflow import TransferMeteoWorkflow
from aiida_flexpart.workflows.child_sim_workflow import FlexpartSimWorkflow


class ParentWorkflow(engine.WorkChain):
    """Flexpart multi-dates workflow"""
    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)
        #inputs from child
        spec.expose_inputs(TransferMeteoWorkflow)
        spec.expose_outputs(TransferMeteoWorkflow)
        spec.expose_inputs(FlexpartSimWorkflow)
        spec.expose_outputs(FlexpartSimWorkflow)
        spec.outputs.dynamic = True

        spec.outline(
            cls.transfer_meteo,
            cls.run_sim,
            cls.finalize,
        )

    def transfer_meteo(self):
        child_1 = self.submit(TransferMeteoWorkflow,
                              **self.exposed_inputs(TransferMeteoWorkflow))
        return engine.ToContext(child_1=child_1)

    def run_sim(self):
        for i in range(len(self.inputs.simulation_dates)):
            child = self.submit(FlexpartSimWorkflow,
                                **self.exposed_inputs(FlexpartSimWorkflow),
                                date=orm.Int(i))
            self.to_context(workchains=engine.append_(child))

    def finalize(self):
        self.out_many(self.exposed_outputs(self.ctx.child_1, TransferMeteoWorkflow))
        for w in  self.ctx.workchains:
            self.out_many(
                self.exposed_outputs(w, FlexpartSimWorkflow)
                )
