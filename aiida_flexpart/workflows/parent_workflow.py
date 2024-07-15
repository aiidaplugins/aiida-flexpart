# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.engine import calcfunction
from aiida_flexpart.workflows.child_meteo_workflow import TransferMeteoWorkflow
from aiida_flexpart.workflows.child_sim_workflow import FlexpartSimWorkflow
import time
"""@engine.calcfunction
def my_sleep():
    return orm.Bool(True)"""


class ParentWorkflow(engine.WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)

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

    def condition(self):
        return self.ctx.index < len(self.inputs.simulation_dates)

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

    """def not_all_complete(self):
        time.sleep(10)
        for workchain in self.node.called:
            if workchain.is_finished == False:
                return True
        return False

    def wait_to_complete(self):
        res = my_sleep()
        engine.ToContext(sleep_job=res)"""

    def finalize(self):
        self.out_many(
            self.exposed_outputs(self.ctx.child_1, TransferMeteoWorkflow))
        for w in self.ctx.workchains:
            self.out_many(self.exposed_outputs(w, FlexpartSimWorkflow))
