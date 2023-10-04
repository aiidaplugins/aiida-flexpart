# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, plugins, orm
from aiida_shell import launch_shell_job
from aiida.engine import calcfunction, while_
import datetime

FlexpartCalculation = plugins.CalculationFactory('flexpart.cosmo')

def get_simulation_period(date,
                   age_class,
                   release_duration,
                   simulation_direction
                   ):
        """Dealing with simulation times."""
        #get dates of all range
        simulation_beginning_date = datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
        age_class_time = datetime.timedelta(seconds=age_class)
        release_duration = datetime.timedelta(seconds=release_duration)
        release_beginning_date = simulation_beginning_date
        release_ending_date = simulation_beginning_date + release_duration * simulation_direction
        simulation_ending_date = release_ending_date + age_class_time * simulation_direction

        # FLEXPART requires the beginning date to be lower than the ending date.
        if simulation_beginning_date > simulation_ending_date:
            simulation_beginning_date, simulation_ending_date = simulation_ending_date, simulation_beginning_date
        
        return datetime.datetime.strftime(simulation_ending_date,'%Y%m%d%H'), datetime.datetime.strftime(simulation_beginning_date,'%Y%m%d%H')


class FlexpartMultipleDatesWorkflow(engine.WorkChain):
    """Flexpart multi-dates workflow"""
    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)
        # Inputs
        spec.input('code', valid_type=orm.AbstractCode)
        spec.input('simulation_dates',
                   valid_type=orm.List,
                   help='A list of the starting dates of the simulations')
        spec.input('locations',
                   valid_type=orm.Dict,
                   help='Dictionary of locations properties.')
        spec.input('meteo_inputs',
                   valid_type=orm.Dict,
                   help='Meteo models input params.')
        spec.input('integration_time',
                   valid_type=orm.Int,
                   help='Integration time in hours')
        spec.input('outgrid', valid_type=orm.Dict)
        spec.input('outgrid_nest', valid_type=orm.Dict, required=False)

        spec.input('model', valid_type=orm.Str, required=True,
                   help=' ')
        spec.input('gribdir', valid_type=orm.Str, required=True,
                   help=' ')

        spec.input('outgrid', valid_type=orm.Dict)
        spec.input('meteo_path', valid_type=orm.RemoteData,
        required=True, help='Path to the folder containing the meteorological input data.')
        
        spec.input('species', valid_type=orm.RemoteData, required=True)
        spec.input_namespace('land_use',
                             valid_type=orm.RemoteData,
                             required=False,
                             dynamic=True,
                             help='#TODO')

        spec.expose_inputs(FlexpartCalculation,
                           include=['metadata.options'],
                           namespace='flexpart')

        # Outputs
        #spec.output('output_file', valid_type=orm.SinglefileData)
        spec.outputs.dynamic = True
        # What the workflow will do, step-by-step
        spec.outline(
            cls.setup,
            while_(cls.condition)(
            cls.prepare_meteo_folder,
            cls.run_simulation,
            ),
            cls.results,
        )
    def condition(self):
        return True if self.ctx.index < len(self.ctx.simulation_dates) else False

    def setup(self):
        """Prepare a simulation."""
        self.ctx.index = 0
        command = {
            'simulation_direction':
            -1,  # 1 for forward simulation, -1 for backward simulation.
            # 'simulation_date': self.inputs.simulation_date.value,  # YYYY-MM-DD HH:MI:SS beginning date of simulation.
            'age_class': self.inputs.integration_time * 3600,  # seconds
            'release_chunk': 3600 * 3,  # seconds
            'release_duration': 3600 * 24,  # seconds
            'output_every_seconds': 10800,  # Output every xxx seconds.
            'time_average_of_output_seconds':
            10800,  # Time average of output (in seconds).
            # 'sampling_rate_of_output': 60, # Sampling rate of output (in seconds).
            'particle_splitting_time_constant':
            999999999,  # Time constant for particle splitting (in seconds).
            # 'synchronisation_interval': 60, # Synchronisation interval of flexpart (in seconds).
            'smaller_than_tl_factor':
            2.0,  #  Factor, by which time step must be smaller than TL.
            'vertical_motion_time_decrease':
            4,  # Decrease of time step for vertical motion by factor ifine.
            'concentration_output':
            9,  # Determines how the output shall be made: concentration (ng/m3, Bq/m3), mixing ratio (pptv), or both,
            # or plume trajectory mode, or concentration + plume trajectory mode. In plume trajectory mode, output is
            # in the form of average trajectories.
            'particle_dump':
            4,  # Particle dump: 0 no, 1 every output interval, 2 only at end, 4 when leaving domain.
            'subgrid_terrain_effect_parameterization':
            True,  # Include ubgrid terrain effect parameterization.
            # 'convection_parametrization': 2, #  Convection: 2 tiedtke, 1 emanuel, 0 no.
            'age_spectra':
            True,  # Switch on/off the calculation of age spectra: if yes, the file AGECLASSES must be available.
            'dumped_particle_data':
            False,  #  Continue simulation with dumped particle data.
            'output_for_each_release':
            True,  # Create an ouput file for each release location.
            'calculate_fluxes': False,  # Calculate fluxes.
            'domain_filling_trajectory':
            0,  #  Domain-filling trajectory option: 1 yes, 0 no, 2 strat, 3 tracer.
            'concentration_units_at_source':
            1,  # 1=mass unit , 2=mass mixing ratio unit.
            'concentration_units_at_receptor':
            2,  # 1=mass unit , 2=mass mixing ratio unit.
            'quasilagrangian_mode_to_track_particles':
            False,  # Quasilagrangian mode to track individual particles.
            # 'nested_output': True, # Shall nested output be used?
            'cosmo_model_mixing_height':
            False,  # Shall cosmo model mixing height be used if present?
            'cosmo_grid_relaxation_zone_width':
            50.0,  # Width of cosmo grid relaxation zone in km
        }

        # Add meteo model params to simulation's setup
        command.update(self.inputs.meteo_inputs)

        self.ctx.command = orm.Dict(dict=command)

        self.ctx.input_phy = orm.Dict(
            dict={
                'use2mTemperatures': False,
                'useLocalHmix': True,
                'localWadjust': False,
                'turbmesoscale': 0.0,
                'd_trop': 50.0,
                'd_strat': 0.5,
                'hmixmin': 50.0,
                'hmixmax': 4500.0,
            })

        self.ctx.outgrid = self.inputs.outgrid

        self.ctx.outgrid_nest = self.inputs.outgrid_nest

        self.ctx.release_settings = orm.Dict(
            dict={
                'particles_per_release': 50000,
                'mass_per_release': [1.0],
                'list_of_species': [24],
            })

        self.ctx.locations = self.inputs.locations
        self.ctx.species = self.inputs.species
        self.ctx.land_use = self.inputs.land_use
        self.ctx.simulation_dates=self.inputs.simulation_dates

     
    def prepare_meteo_folder(self):
        code = orm.load_code('test_bash_2@daint-direct')
       
        e_date, s_date = get_simulation_period(self.ctx.simulation_dates[self.ctx.index],
                                    self.ctx.command.get_dict()["age_class"],
                                    self.ctx.command.get_dict()["release_duration"],
                                    self.ctx.command.get_dict()["simulation_direction"])
        
        results, node = launch_shell_job(
                    code,                           
                    arguments=' -s {sdate} -e {edate} -g {gribdir} -m {model} -a',
                    nodes={
                        'sdate': orm.Str(s_date),
                        'edate': orm.Str(e_date),
                        'gribdir': self.inputs.gribdir,
                        'model': self.inputs.model
                    })

    def run_simulation(self):
            """Run calculations for equation of state."""
            # Set up calculation.
        
            builder = FlexpartCalculation.get_builder()
            new_dict = self.ctx.command.get_dict()
            new_dict['simulation_date'] = self.ctx.simulation_dates[self.ctx.index]
            builder.code = self.inputs.code
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
                                   

            builder.metadata.description = 'Test workflow to submit a flexpart calculation'

            # Walltime, memory, and resources.
            builder.metadata.options = self.inputs.flexpart.metadata.options

            # Ask the workflow to continue when the results are ready and store them in the context
            running = self.submit(builder)
            self.to_context(calculations=engine.append_(running))
            self.ctx.index += 1

    def results(self):
        """Process results."""
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f'calculation_{indx}_output_file',
                     calculation.outputs.output_file)
