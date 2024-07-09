#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a multi dates workflow."""

import pathlib
import datetime
import click
import yaml
from aiida import orm, plugins, engine, cmdline
from aiida.common.datastructures import StashMode


def read_yaml_data(data_filename: str, names=None) -> dict:
    """Read in a YAML data file as a dictionary"""
    data_path = pathlib.Path(data_filename)
    with data_path.open('r', encoding='utf-8') as fp:
        yaml_data = yaml.safe_load(fp)

    return {key: value
            for key, value in yaml_data.items()
            if key in names} if names else yaml_data


def simulation_dates_parser(date_list: list) -> list:
    """
    Parse a range of dates and returns a list of date strings.

    Examples:
        2021-01-02--2021-01-10 -> [2021-01-02 00:00:00, 2021-01-02 00:00:00, ..., 2021-01-10 00:00:00]
        2021-01-02, 2021-01-10 -> [2021-01-02 00:00:00, 2021-01-10 00:00:00]
        2021-01-02 -> [2021-01-02 00:00:00,]
    """
    dates = []
    for date_string in date_list:
        if ',' in date_string:
            dates += [
                date.strip() + ' 00:00:00' for date in date_string.split(',')
            ]
        elif '--' in date_string:
            date_start, date_end = list(
                map(lambda date: datetime.datetime.strptime(date, '%Y-%m-%d'),
                    date_string.split('--')))
            dates += [
                date.strftime('%Y-%m-%d 00:00:00') for date in [
                    date_start + datetime.timedelta(days=x)
                    for x in range(0, (date_end - date_start).days + 1)
                ]
            ]
        else:
            dates += [date_string.strip() + ' 00:00:00']

    return orm.List(list=dates)


def test_run(flexpart_code):
    """Run workflow."""
    user_name='lfernand'
    simulation_dates = simulation_dates_parser(['2020-02-05'])

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
    
    #builder starts
    workflow = plugins.WorkflowFactory('flexpart.multi_workflow')
    builder = workflow.get_builder()
    builder.fcosmo_code = flexpart_code
    builder.check_meteo_cosmo_code =  orm.load_code('check-cosmo-data@daint-direct-106')
    builder.simulation_dates = simulation_dates

    builder.model=orm.Str('cosmo7')
    builder.meteo_path = meteo_path
    builder.gribdir=orm.Str(f'/scratch/snx3000/{user_name}/FLEXPART_input/')
    builder.outgrid = orm.Dict(
        dict=read_yaml_data('inputs/outgrid.yaml', names=[
            'Europe',
        ])['Europe'])
    builder.outgrid_nest = orm.Dict(dict=read_yaml_data(
        'inputs/outgrid_nest.yaml', names=[
            'Europe',
        ])['Europe'])  # optional input
   
    #model settings
    builder.command = orm.Dict(dict=read_yaml_data('inputs/command.yaml'))
    builder.input_phy = orm.Dict(dict=read_yaml_data('inputs/input_phy.yaml'))
    builder.release_settings = orm.Dict(dict=read_yaml_data('inputs/release.yaml'))
    builder.locations = orm.Dict(
        dict=read_yaml_data('inputs/locations.yaml', names=[
            'TEST_32',
        ]))
    
    builder.meteo_inputs = orm.Dict(
        dict=read_yaml_data('inputs/meteo_inputs.yaml', names=[
            'cosmo7',
        ])['cosmo7'])
    builder.integration_time = orm.Int(24)
    builder.species = species
    builder.land_use = {
        'glc': glc,
        'surfdata': surfdata,
        'surfdepo': surfdepo,
    }

    builder.flexpart.metadata.options.stash = {
        'source_list': ['aiida.out','partposit_inst', 'header', 'grid_time_*.nc'],
        'target_base': f'/store/empa/em05/{user_name}/aiida_stash',
        'stash_mode': StashMode.COPY.value,
    }
    engine.run(builder)


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