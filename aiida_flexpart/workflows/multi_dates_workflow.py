# -*- coding: utf-8 -*-
"""Equation of State WorkChain."""
from aiida import engine, plugins, orm

FlexpartCalculation = plugins.CalculationFactory('flexpart.cosmo')

class FlexpartMultipleDatesWorkflow(engine.WorkChain):
    """WorkChain to compute Equation of State using Quantum Espresso."""

    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)
        spec.input('code', valid_type=orm.Code)
        spec.input('simulation_date', valid_type=orm.Str)
        spec.output('output_file', valid_type=orm.SinglefileData)
        # What the workflow will do, step-by-step
        spec.outline(
            cls.setup,
            cls.run_simulation,
            cls.results,
        )

    def setup(self):
        """Prepare a simulation."""
        self.ctx.command = orm.Dict(dict={
            'simulation_direction': -1, # 1 for forward simulation, -1 for backward simulation.
            'simulation_date': self.inputs.simulation_date.value,  # YYYY-MM-DD HH:MI:SS beginning date of simulation.
            'age_class': 3600 * 24, # seconds
            'release_chunk': 3600 * 3, # seconds
            'release_duration': 3600*24, # seconds
            'output_every_seconds': 10800,  # Output every xxx seconds.
            'time_average_of_output_seconds': 10800, # Time average of output (in seconds).
            'sampling_rate_of_output': 60, # Sampling rate of output (in seconds).
            'particle_splitting_time_constant': 999999999, # Time constant for particle splitting (in seconds).
            'synchronisation_interval': 60, # Synchronisation interval of flexpart (in seconds).
            'smaller_than_tl_factor': 2.0, #  Factor, by which time step must be smaller than TL.
            'vertical_motion_time_decrease': 4, # Decrease of time step for vertical motion by factor ifine.
            'concentration_output': 9,  # Determines how the output shall be made: concentration (ng/m3, Bq/m3), mixing ratio (pptv), or both, or plume trajectory mode, or concentration + plume trajectory mode. In plume trajectory mode, output is in the form of average trajectories.
            'particle_dump': 4, # Particle dump: 0 no, 1 every output interval, 2 only at end, 4 when leaving domain.
            'subgrid_terrain_effect_parameterization': True, # Include ubgrid terrain effect parameterization.
            'convection_parametrization': 2, #  Convection: 2 tiedtke, 1 emanuel, 0 no.
            'age_spectra': True,  # Switch on/off the calculation of age spectra: if yes, the file AGECLASSES must be available.
            'dumped_particle_data': False, #  Continue simulation with dumped particle data.
            'output_for_each_release': True, # Create an ouput file for each release location.
            'calculate_fluxes': False, # Calculate fluxes.
            'domain_filling_trajectory': 0, #  Domain-filling trajectory option: 1 yes, 0 no, 2 strat, 3 tracer.
            'concentration_units_at_source': 1, # 1=mass unit , 2=mass mixing ratio unit.
            'concentration_units_at_receptor': 2, # 1=mass unit , 2=mass mixing ratio unit.
            'quasilagrangian_mode_to_track_particles': False, # Quasilagrangian mode to track individual particles.
            'nested_output': True, # Shall nested output be used? 
            'cosmo_model_mixing_height': False, # Shall cosmo model mixing height be used if present?
            'cosmo_grid_relaxation_zone_width': 50.0, # Width of cosmo grid relaxation zone in km
        })

        self.ctx.input_phy = orm.Dict(dict={
            'use2mTemperatures': False,
            'useLocalHmix': True,
            'localWadjust': False,
            'turbmesoscale': 0.0,
            'd_trop': 50.0,
            'd_strat': 0.5,
            'hmixmin': 50.0,
            'hmixmax': 4500.0,
        })

        self.ctx.outgrid = orm.Dict(dict={
            'output_grid_type': 0, #  1 for coos provided in rotated system, 0 for geographical.
            'longitude_of_output_grid': -12.00, # Longitude of lower left corner of output grid (left boundary of the first grid cell - not its centre).
            'latitude_of_output_grid': 36.00, # Latitude of lower left corner of output grid  (lower boundary of the first grid cell - not its centre).
            'number_of_grid_points_x': 207, # Number of grid points in x direction (= # of cells + 1).
            'number_of_grid_points_y': 179, # Number of grid points in y direction (= # of cells + 1).
            'grid_distance_x': 0.16, # Grid distance in x direction.
            'grid_distance_y': 0.12, # Grid distance in y direction.
            'heights_of_levels': [50.0, 100.0, 200.0, 500.0, 15000.0], # List of heights of leves (upper boundary).
        })

        self.ctx.outgrid_nest = orm.Dict(dict={
            'output_grid_type': 0, #  1 for coos provided in rotated system, 0 for geographical.
            'longitude_of_output_grid': 4.96, # Longitude of lower left corner of output grid (left boundary of the first grid cell - not its centre).
            'latitude_of_output_grid': 45.48, # Latitude of lower left corner of output grid  (lower boundary of the first grid cell - not its centre).
            'number_of_grid_points_x': 305, # Number of grid points in x direction (= # of cells + 1).
            'number_of_grid_points_y': 205, # Number of grid points in y direction (= # of cells + 1).
            'grid_distance_x': 0.02, # Grid distance in x direction.
            'grid_distance_y': 0.015, # Grid distance in y direction.
        })

        self.ctx.release_settings = orm.Dict(dict={
            'particles_per_release': 50000,
            'mass_per_release': [1.0],
            'list_of_species': [24],
        })

        # TODO: might be a good input for the workflow
        self.ctx.locations = orm.List(list=['TEST_32', 'TEST_200'])

        self.ctx.glc = orm.RemoteData(remote_path='/users/ebaldi/resources/flexpart/GLC2000', computer=self.inputs.code.computer)
        self.ctx.species = orm.RemoteData(remote_path='/users/ebaldi/resources/flexpart/SPECIES', computer=self.inputs.code.computer)
        self.ctx.surfdata = orm.RemoteData(remote_path='/users/ebaldi/resources/flexpart/surfdata.t', computer=self.inputs.code.computer)
        self.ctx.surfdepo = orm.RemoteData(remote_path='/users/ebaldi/resources/flexpart/surfdepo.t', computer=self.inputs.code.computer)

    def run_simulation(self):
        """Run calculations for equation of state."""
        # Set up calculation.
        builder = FlexpartCalculation.get_builder()
        builder.code = self.inputs.code
        builder.model_settings = {
            'release_settings': self.ctx.release_settings,
            'locations': self.ctx.locations,
            'command': self.ctx.command,
            'input_phy': self.ctx.input_phy,
            }
        builder.outgrid = self.ctx.outgrid
        builder.outgrid_nest = self.ctx.outgrid_nest
        builder.species = self.ctx.species
        builder.land_use = {
            'glc': self.ctx.glc,
            'surfdata': self.ctx.surfdata,
            'surfdepo': self.ctx.surfdepo,
            }

        builder.metadata = {'description': 'Test workflow to submit a flexpart calculation'}

        # Ask the workflow to continue when the results are ready and store them in the context
        running = self.submit(builder) # self.submit.to_context.append -> to submit multiple calculations
        return engine.ToContext(calculation=running)

    def results(self):
        """Process results."""
        self.out('output_file', self.ctx.calculation.outputs.output_file)