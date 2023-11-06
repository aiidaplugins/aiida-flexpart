# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, plugins, orm
from aiida_shell import launch_shell_job
from aiida.engine import calcfunction, while_, if_
import datetime

FlexpartCalculation = plugins.CalculationFactory('flexpart.cosmo')
FlexpartIfsCalculation = plugins.CalculationFactory('flexpart.ifs')

#possible models
cosmo_models = ['cosmo7', 'cosmo1', 'kenda1']
ECMWF_models = ['IFS_GL_05', 'IFS_GL_1', 'IFS_EU_02', 'IFS_EU_01']

def get_simulation_period(date,
                   age_class_time,
                   release_duration,
                   simulation_direction
                   ):
        """Dealing with simulation times."""
        #initial values
        simulation_beginning_date = datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
        age_class_time = datetime.timedelta(seconds=age_class_time)
        release_duration = datetime.timedelta(seconds=release_duration+3600)

        if simulation_direction>0: #forward
            simulation_ending_date=simulation_beginning_date+release_duration+age_class_time
        else: #backward
           simulation_ending_date=release_duration+simulation_beginning_date
           simulation_beginning_date-=age_class_time
        
        return datetime.datetime.strftime(simulation_ending_date,'%Y%m%d%H'), datetime.datetime.strftime(simulation_beginning_date,'%Y%m%d%H')


class FlexpartMultipleDatesWorkflow(engine.WorkChain):
    """Flexpart multi-dates workflow"""
    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)

        #codes
        spec.input('fcosmo_code', valid_type=orm.AbstractCode)
        spec.input('check_meteo_cosmo_code', valid_type=orm.AbstractCode)
        spec.input('fifs_code', valid_type=orm.AbstractCode)
        spec.input('check_meteo_ifs_code', valid_type=orm.AbstractCode)

        # Basic Inputs
        spec.input('simulation_dates', valid_type=orm.List,
                   help='A list of the starting dates of the simulations')
        spec.input('model', valid_type=orm.Str, required=True)
        spec.input('model_offline', valid_type=orm.Str, required=True)
        spec.input('offline_integration_time', valid_type=orm.Int)
        spec.input('integration_time', valid_type=orm.Int, help='Integration time in hours')
        spec.input("parent_calc_folder",
            valid_type=orm.RemoteData,
            required=False,
            help="Working directory of a previously ran calculation to restart from."
        )
        
        #model settings
        spec.input('input_phy', valid_type=orm.Dict)
        spec.input('command', valid_type=orm.Dict)
        spec.input('release_settings', valid_type=orm.Dict)
        spec.input('locations', valid_type=orm.Dict,
                   help='Dictionary of locations properties.')
        
        #meteo related inputs
        spec.input('meteo_inputs', valid_type=orm.Dict,
                   help='Meteo models input params.')
        spec.input('meteo_inputs_offline', valid_type=orm.Dict,required=False,
                   help='Meteo models input params.')
        spec.input('meteo_path', valid_type=orm.RemoteData,
        required=True, help='Path to the folder containing the meteorological input data.')
        spec.input('meteo_path_offline', valid_type=orm.RemoteData,
        required=False, help='Path to the folder containing the meteorological input data.')
        spec.input('gribdir', valid_type=orm.Str, required=True)

        #others
        spec.input('outgrid', valid_type=orm.Dict)
        spec.input('outgrid_nest', valid_type=orm.Dict, required=False)
        spec.input('species', valid_type=orm.RemoteData, required=True)
        spec.input_namespace('land_use',
                             valid_type=orm.RemoteData,
                             required=False,
                             dynamic=True,
                             help='#TODO')
        spec.input_namespace('land_use_ifs', valid_type=orm.RemoteData, required=False, dynamic=True)

        spec.expose_inputs(FlexpartCalculation,
                           include=['metadata.options'],
                           namespace='flexpart')
        spec.expose_inputs(FlexpartIfsCalculation,
                           include=['metadata.options'],
                           namespace='flexpartifs')

        # Outputs
        #spec.output('output_file', valid_type=orm.SinglefileData)
        spec.outputs.dynamic = True
        # What the workflow will do, step-by-step
        spec.outline(
            cls.setup,
            while_(cls.condition)(
            if_(cls.run_cosmo)(
                if_(cls.prepare_meteo_folder_cosmo)(
                cls.run_cosmo_simulation
                )
            ),
            if_(cls.run_ifs)(
                if_(cls.prepare_meteo_folder_ifs)(
                cls.run_ifs_simulation
                )
            ),
            if_(cls.run_offline)(
                if_(cls.prepare_meteo_folder_ifs)(
                cls.run_ifs_simulation
                )
            )
            ),
            cls.results,
        )

    def condition(self):
        return True if self.ctx.index < len(self.ctx.simulation_dates) else False
    
    def run_cosmo(self):
         return True if self.inputs.model in cosmo_models else False
    
    def run_ifs(self):
         return True if self.inputs.model in ECMWF_models else False
    
    def run_offline(self):
         if self.inputs.model_offline in ECMWF_models and self.inputs.model is not None:
              self.ctx.index-=1
              return True
         elif self.inputs.model_offline in ECMWF_models and self.inputs.model is None:
              return True
         return False

    def setup(self):
        """Prepare a simulation."""

        self.report(f'starting setup')

        self.ctx.index = 0
        self.ctx.simulation_dates = self.inputs.simulation_dates
        self.ctx.integration_time = self.inputs.integration_time
        self.ctx.offline_integration_time = self.inputs.offline_integration_time
       
        #model settings
        self.ctx.release_settings = self.inputs.release_settings
        self.ctx.command = self.inputs.command
        self.ctx.input_phy = self.inputs.input_phy
        self.ctx.locations = self.inputs.locations
        
        #others
        self.ctx.outgrid = self.inputs.outgrid
        self.ctx.outgrid_nest = self.inputs.outgrid_nest
        self.ctx.species = self.inputs.species
        self.ctx.land_use = self.inputs.land_use

    def prepare_meteo_folder_ifs(self):
        age_class_ = self.inputs.integration_time.value * 3600
        if self.ctx.offline_integration_time>0:
                age_class_ = self.inputs.offline_integration_time.value * 3600
        e_date, s_date = get_simulation_period(self.ctx.simulation_dates[self.ctx.index],
                                    age_class_,
                                    self.ctx.command.get_dict()["release_duration"],
                                    self.ctx.command.get_dict()["simulation_direction"])
        
        self.report(f'prepare meteo from {s_date} to {e_date}')

        results, node = launch_shell_job(
                    self.inputs.check_meteo_ifs_code,                           
                    arguments=' -s {sdate} -e {edate} -a',
                    nodes={
                        'sdate': orm.Str(s_date),
                        'edate': orm.Str(e_date),
                    })

        if node.is_finished_ok:
             self.report('meteo files transferred successfully')
             return True
        else:
             self.report('failed to transfer meteo files')
             self.ctx.index += 1
             return False
    
    def prepare_meteo_folder_cosmo(self):
        e_date, s_date = get_simulation_period(self.ctx.simulation_dates[self.ctx.index],
                                    self.inputs.integration_time.value * 3600,
                                    self.ctx.command.get_dict()["release_duration"],
                                    self.ctx.command.get_dict()["simulation_direction"])
        
        self.report(f'prepare meteo from {s_date} to {e_date}')

        results, node = launch_shell_job(
                    self.inputs.check_meteo_cosmo_code,                           
                    arguments=' -s {sdate} -e {edate} -g {gribdir} -m {model} -a',
                    nodes={
                        'sdate': orm.Str(s_date),
                        'edate': orm.Str(e_date),
                        'gribdir': self.inputs.gribdir,
                        'model': self.inputs.model
                    })

        if node.is_finished_ok:
             self.report('meteo files transferred successfully')
             return True
        else:
             self.report('failed to transfer meteo files')
             self.ctx.index += 1
             return False

    def run_cosmo_simulation(self):
            """Run calculations for equation of state."""
     
            self.report('starting flexpart cosmo')

            builder = FlexpartCalculation.get_builder()
            builder.code = self.inputs.fcosmo_code

            #update command file 
            new_dict = self.ctx.command.get_dict()
            new_dict['simulation_date'] = self.ctx.simulation_dates[self.ctx.index]
            new_dict['age_class'] = self.inputs.integration_time * 3600
            new_dict.update(self.inputs.meteo_inputs)

            #model settings
            builder.model_settings = {
                'release_settings': self.ctx.release_settings,
                'locations': self.ctx.locations,
                'command': orm.Dict(dict=new_dict),
                'input_phy': self.ctx.input_phy,
            }

            builder.outgrid = self.ctx.outgrid
            builder.outgrid_nest = self.ctx.outgrid_nest
            builder.species = self.ctx.species
            builder.land_use = self.ctx.land_use
            builder.meteo_path = self.inputs.meteo_path

            # Walltime, memory, and resources.
            builder.metadata.description = 'Test workflow to submit a flexpart calculation'
            builder.metadata.options = self.inputs.flexpart.metadata.options
            

            # Ask the workflow to continue when the results are ready and store them in the context
            running = self.submit(builder)
            self.to_context(calculations=engine.append_(running))
    
            self.ctx.index += 1

    def run_ifs_simulation(self):
            """Run calculations for equation of state."""
            # Set up calculation.
            self.report(f'Running FIFS for {self.ctx.simulation_dates[self.ctx.index]}')
            builder = FlexpartIfsCalculation.get_builder()
            builder.code = self.inputs.fifs_code
       
            #changes in the command file
            new_dict = self.ctx.command.get_dict()
            new_dict['simulation_date'] = self.ctx.simulation_dates[self.ctx.index]

            if self.inputs.model_offline in ECMWF_models:
                new_dict['age_class'] = self.ctx.offline_integration_time * 3600
                new_dict['dumped_particle_data'] = True

                if self.inputs.model is not None:
                    self.ctx.parent_calc_folder = self.ctx.calculations[-1].outputs.remote_folder
                    self.report(f'starting from: {self.ctx.parent_calc_folder}')
                else:
                    self.ctx.parent_calc_folder = self.inputs.parent_calc_folder

                builder.meteo_path = self.inputs.meteo_path_offline
                builder.parent_calc_folder = self.ctx.parent_calc_folder
                new_dict.update(self.inputs.meteo_inputs_offline)
            else:
                new_dict['age_class'] = self.inputs.integration_time * 3600
                builder.meteo_path = self.inputs.meteo_path
                new_dict.update(self.inputs.meteo_inputs)

            #model settings
            builder.model_settings = {
                'release_settings': self.ctx.release_settings,
                'locations': self.ctx.locations,
                'command': orm.Dict(dict=new_dict),
            }
    
            builder.outgrid = self.ctx.outgrid
            builder.outgrid_nest = self.ctx.outgrid_nest
            builder.species = self.ctx.species
            builder.land_use = self.inputs.land_use_ifs
   
            # Walltime, memory, and resources.
            builder.metadata.description = 'Test workflow to submit a flexpart calculation'
            builder.metadata.options = self.inputs.flexpartifs.metadata.options

            # Ask the workflow to continue when the results are ready and store them in the context
            running = self.submit(builder)
            self.to_context(calculations=engine.append_(running))

            self.ctx.index += 1

    def results(self):
        """Process results."""
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f'calculation_{indx}_output_file',
                     calculation.outputs.output_file)
