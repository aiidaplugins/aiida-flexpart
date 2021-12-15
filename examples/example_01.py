#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a test calculation on localhost.

Usage: ./example_01.py
"""
from pathlib import Path
import click
from aiida import cmdline, engine, orm
from aiida.plugins import DataFactory, CalculationFactory
from aiida_flexpart import helpers

INPUT_DIR = Path(__file__).resolve().parent / 'input_files'

def test_run(flexpart_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """

    # Prepare input parameters

    SinglefileData = DataFactory('singlefile')
    outgrid = SinglefileData(
        file=INPUT_DIR/'OUTGRID')
    outgrid_nest = SinglefileData(
        file=INPUT_DIR/'OUTGRID_NEST')
    releases = SinglefileData(
        file=INPUT_DIR/'RELEASES')
    #model_settings = SinglefileData(
    #    file=INPUT_DIR/'COMMAND')
    age_classes = SinglefileData(
        file=INPUT_DIR/'AGECLASSES')


    input_phy = orm.Dict(dict={
        'use2mTemperatures': False,
        'useLocalHmix': True,
        'localWadjust': False,
        'turbmesoscale': 0.0,
        'd_trop': 50.0,
        'd_strat': 0.5,
        'hmixmin': 50.0,
        'hmixmax': 4500.0,
    }
    )

    # Links to the remote files/folders.
    glc = orm.RemoteData(remote_path='/users/yaa/resources/flexpart/GLC2000', computer=flexpart_code.computer)
    species = orm.RemoteData(remote_path='/users/yaa/resources/flexpart/SPECIES', computer=flexpart_code.computer)
    surfdata = orm.RemoteData(remote_path='/users/yaa/resources/flexpart/surfdata.t', computer=flexpart_code.computer)
    surfdepo = orm.RemoteData(remote_path='/users/yaa/resources/flexpart/surfdepo.t', computer=flexpart_code.computer)

    command = orm.Dict(dict={
        'simulation_direction': -1, # 1 for forward simulation, -1 for backward simulation.
        'simulation_beginning_date': [20201231, 000000],  # YYYYMMDD HHMISS beginning date of simulation.
        'simulation_ending_date': [20210102, 000000],  # YYYYMMDD HHMISS ending date of simulation.
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

    # set up calculation
    inputs = {
        'model_settings': {
            'releases_settings': orm.Dict(dict={'a':1}),
            'releases_times': orm.Dict(dict={'b':2}),
            'command': command,
        },
        'code': flexpart_code,
        'outgrid': outgrid,
        'outgrid_nest': outgrid_nest,
        'releases': releases,
        'input_phy': input_phy,
        'age_classes': age_classes,
        'species': species,
        'land_use':{
            'glc': glc,
            'surfdata': surfdata,
            'surfdepo': surfdepo,
        },

        'metadata': {
            'description': 'Test job submission with the aiida_flexpart plugin',
        },
    }

    # Note: in order to submit your calculation to the aiida daemon, do:
    # from aiida.engine import submit
    # future = submit(CalculationFactory('flexpart'), **inputs)
    result = engine.run(CalculationFactory('flexpart.cosmo'), **inputs)


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
def cli(code):
    """Run example.

    Example usage: $ ./example_01.py --code diff@localhost

    Alternative (creates diff@localhost-test code): $ ./example_01.py

    Help: $ ./example_01.py --help
    """
    test_run(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
