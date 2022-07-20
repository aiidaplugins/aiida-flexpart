# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, plugins, orm

FlexpartCalculation = plugins.CalculationFactory('flexpart.cosmo')


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
        spec.input(
            'meteo_path',
            valid_type=orm.RemoteData,
            required=True,
            help='Path to the folder containing the meteorological input data.'
        )
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
            cls.run_simulation,
            cls.results,
        )

    def setup(self):
        """Prepare a simulation."""
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
        self.ctx.meteo_path = self.inputs.meteo_path
        self.ctx.species = self.inputs.species
        self.ctx.land_use = self.inputs.land_use

    def run_simulation(self):
        """Run calculations for equation of state."""
        # Set up calculation.
        for date in self.inputs.simulation_dates:
            builder = FlexpartCalculation.get_builder()
            new_dict = self.ctx.command.get_dict()
            new_dict['simulation_date'] = date
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
            builder.meteo_path = self.ctx.meteo_path
            builder.land_use = self.ctx.land_use

            builder.metadata.description = 'Test workflow to submit a flexpart calculation'

            # Walltime, memory, and resources.
            builder.metadata.options = self.inputs.flexpart.metadata.options

            # Ask the workflow to continue when the results are ready and store them in the context
            running = self.submit(builder)
            self.to_context(calculations=engine.append_(running))

    def results(self):
        """Process results."""
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f'calculation_{indx}_output_file',
                     calculation.outputs.output_file)
