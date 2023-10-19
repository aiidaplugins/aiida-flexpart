#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a test calculation on localhost.

Usage: ./example_01.py
"""
import pathlib
import click
import yaml
from aiida import cmdline, engine, orm
from aiida.plugins import CalculationFactory
from aiida.common.datastructures import StashMode

INPUT_DIR = pathlib.Path(__file__).resolve().parent / 'input_files'


def read_yaml_data(data_filename: str, names=None) -> dict:
    """Read in a YAML data file as a dictionary"""
    data_path = pathlib.Path(data_filename)
    with data_path.open('r', encoding='utf-8') as fp:
        yaml_data = yaml.safe_load(fp)

    return {key: value
            for key, value in yaml_data.items()
            if key in names} if names else yaml_data


def test_run(flexpart_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """

    # Prepare input parameters
    user_name='lfernand'

    command = orm.Dict(
        dict=read_yaml_data('inputs/command.yaml'))
    
    input_phy = orm.Dict(
        dict=read_yaml_data('inputs/input_phy.yaml'))
    
    outgrid = orm.Dict(
        dict=read_yaml_data('inputs/outgrid.yaml', names=['Europe'])['Europe'])

    outgrid_nest = orm.Dict(
        dict=read_yaml_data('inputs/outgrid_nest.yaml', names=['Europe'])['Europe'])

    release_settings = orm.Dict(
        dict=read_yaml_data('inputs/release.yaml'))
    
    locations = orm.Dict(
        dict=read_yaml_data('inputs/locations.yaml', names=['TEST_32',
                                                     'TEST_200']))

    # Links to the remote files/folders.
    glc = orm.RemoteData(remote_path=f'/users/{user_name}/resources/flexpart/GLC2000',
                         computer=flexpart_code.computer)
    species = orm.RemoteData(
        remote_path=f'/users/{user_name}/resources/flexpart/SPECIES',
        computer=flexpart_code.computer)
    surfdata = orm.RemoteData(
        remote_path=f'/users/{user_name}/resources/flexpart/surfdata.t',
        computer=flexpart_code.computer)
    surfdepo = orm.RemoteData(
        remote_path=f'/users/{user_name}/resources/flexpart/surfdepo.t',
        computer=flexpart_code.computer)
    meteo_path = orm.RemoteData(
        remote_path=f'/scratch/snx3000/{user_name}/FLEXPART_input/cosmo7/',
        computer=flexpart_code.computer)

    # Set up calculation.
    calc = CalculationFactory('flexpart.cosmo')
    builder = calc.get_builder()
    builder.code = flexpart_code
    builder.model_settings = {
        'release_settings':
        release_settings,
        'locations':
        locations,
        'command':
        command,
        'input_phy':
        input_phy,
    }
    builder.outgrid = outgrid
    builder.outgrid_nest = outgrid_nest
    builder.species = species
    builder.meteo_path = meteo_path
    builder.land_use = {
        'glc': glc,
        'surfdata': surfdata,
        'surfdepo': surfdepo,
    }

    builder.metadata.description = 'Test job submission with the aiida_flexpart plugin'
    builder.metadata.options.stash = {
        'source_list': ['aiida.out','partposit_inst', 'header', 'grid_time_*.nc'],
        'target_base': f'/store/empa/em05/{user_name}/aiida_stash',
        'stash_mode': StashMode.COPY.value,
    }

    # builder.metadata.dry_run = True
    # builder.metadata.store_provenance = False
    engine.run(builder)
    # result = engine.submit(builder) # submit to aiida daemon


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
