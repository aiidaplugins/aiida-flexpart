from aiida import engine, orm
from aiida.engine import calcfunction
from aiida_flexpart.workflows.child_meteo_workflow import TransferMeteoWorkflow
from aiida_flexpart.workflows.child_sim_workflow import FlexpartSimWorkflow

@calcfunction
def multiply(x, y):
    return orm.Int(x * y)

class ParentWorkflow(engine.WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        #INPUTS
        spec.input('simulation_dates',
                   valid_type=orm.List,
                   help='A list of the starting dates of the simulations')
        
        spec.expose_inputs(TransferMeteoWorkflow)
        spec.expose_outputs(TransferMeteoWorkflow)
        spec.expose_inputs(FlexpartSimWorkflow)
        spec.expose_outputs(FlexpartSimWorkflow)
        spec.outputs.dynamic = True

        spec.outline(
        cls.setup,
        engine.while_(cls.condition)(
            cls.transfer_meteo,
            cls.run_sim
        ),
        cls.finalize,
        )
    def setup(self):
        self.ctx.index=0
    def condition(self):
        return self.ctx.index < len(self.inputs.simulation_dates)
    def transfer_meteo(self):
        child_1 = self.submit(TransferMeteoWorkflow,
                              **self.exposed_inputs(TransferMeteoWorkflow),
                              date=orm.Str(self.inputs.simulation_dates[self.ctx.index]))
        return engine.ToContext(child_1=child_1)

    def run_sim(self):
        #for i in range(len(self.inputs.simulation_dates)):
        child = self.submit(FlexpartSimWorkflow,
                                **self.exposed_inputs(FlexpartSimWorkflow),
                                date=orm.Str(self.inputs.simulation_dates[self.ctx.index]))
        self.to_context(workchains=engine.append_(child))

        self.ctx.index+=1

    def finalize(self):
        self.out_many(self.exposed_outputs(self.ctx.child_1, TransferMeteoWorkflow))
        """for w in  self.ctx.workchains:
            self.out_many(
                self.exposed_outputs(w, FlexpartSimWorkflow)
                )
"""