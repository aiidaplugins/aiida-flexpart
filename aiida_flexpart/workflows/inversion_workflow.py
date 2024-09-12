from aiida import engine, plugins, orm
from datetime import datetime
from dateutil.relativedelta import relativedelta

def make_date_range(start:datetime, end:datetime, months:int, offset:int)->dict:
    dates = {}
    x = start - relativedelta(months=offset)
    end += relativedelta(months=offset)
    while x < end:
        dates[datetime.strftime(x,'%Y-%m-%d')] = datetime.strftime(x+relativedelta(months=months),'%Y-%m-%d')
        x += relativedelta(months=months)
    return dates

def split_chunk(start,end,chunk):

        if chunk =='year':
            return make_date_range(start, end, 12,0)
        elif chunk == '3year':
            return make_date_range(start, end, 12,12)
        elif chunk == 'month':
            return make_date_range(start, end, 1,0)
        else:
            return make_date_range(start, end, 3,1)


InversionCalculation = plugins.CalculationFactory("inversion.calc")
NetCDF = plugins.DataFactory('netcdf.data')

class InversionWorkflow(engine.WorkChain):

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input("inversion_code", valid_type=orm.AbstractCode)

        #extras
        spec.input('name', valid_type=str, non_db=True, required=False)

        spec.input('inv_params',valid_type=orm.Dict,required=True)

        spec.input_namespace('remotes', valid_type = NetCDF, required=True)
        spec.input_namespace('observations',valid_type=NetCDF,required=True)


        spec.input('date_range',valid_type=orm.Str,required=True)
        spec.input('chunk',valid_type=orm.Str,required=True)
        spec.input('chunk_w',valid_type=orm.Str,required=True)

        spec.expose_inputs(InversionCalculation,
                           include=['metadata.options'],
                           namespace='inversioncalc')

        spec.outputs.dynamic = True

        spec.outline(
                cls.setup,
                cls.run_inv,
                cls.finalize,
            )
        
    def setup(self):
        self.ctx.inv_params_dict = self.inputs.inv_params.get_dict()
        self.ctx.inv_params = self.inputs.inv_params.get_dict()
        self.ctx.inv_params.update({'chunk':self.inputs.chunk.value,
                                    'chunk_w':self.inputs.chunk_w.value})

        if 'name' in self.inputs:
             self.node.base.extras.set(
                 self.inputs.name,{
                    'inv_params':self.ctx.inv_params,
                 })
             
    def run_inv(self):

        builder = InversionCalculation.get_builder()
        builder.code = self.inputs.inversion_code
        builder.remotes = self.inputs.remotes
        builder.observations = self.inputs.observations
        builder.chunk = self.inputs.chunk
        builder.chunk_w = self.inputs.chunk_w

        start = datetime.strptime(self.inputs.date_range.value[:10], '%Y-%m-%d')
        end = datetime.strptime(self.inputs.date_range.value[12:], '%Y-%m-%d')
        dates = split_chunk(start, end, self.inputs.chunk_w)

        for s,e in dates.items():
            self.ctx.inv_params_dict.update({'dtm_start':s,
                                            'dtm_end':e})
            builder.start_date = orm.Str(s)
            builder.end_date = orm.Str(e)
            builder.inv_params = orm.Dict(self.ctx.inv_params_dict)
            
            running = self.submit(builder)
            self.to_context(calculations=engine.append_(running))

    def finalize(self):
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f'calculation_{indx}_output_file',
                     calculation.outputs.output_file)