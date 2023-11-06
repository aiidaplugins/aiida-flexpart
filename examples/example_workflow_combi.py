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

    simulation_dates = simulation_dates_parser(['2021-01-07, 2021-01-08'])
    model = 'cosmo7'
    model_offline = 'IFS_GL_05'
    username='lfernand'
    users_address=f'/users/{username}/resources/flexpart/'
    scratch_address=f'/scratch/snx3000/{username}/FLEXPART_input/'


    # Links to the remote files/folders.
    glc = orm.RemoteData(remote_path = users_address+'GLC2000',
                         computer=flexpart_code.computer)
    glc_ifs = orm.RemoteData(remote_path = users_address+'IGBP_int1.dat',
                         computer=flexpart_code.computer)
    species = orm.RemoteData(
        remote_path = users_address+'SPECIES',
        computer=flexpart_code.computer)
    surfdata = orm.RemoteData(
        remote_path = users_address+'surfdata.t',
        computer=flexpart_code.computer)
    surfdepo = orm.RemoteData(
        remote_path = users_address+'surfdepo.t',
        computer=flexpart_code.computer)
    #parent_folder = orm.load_node(pk previous tsk)
    parent_folder = orm.RemoteData(
        remote_path = '/scratch/snx3000/lfernand/aiida/76/8d/cb2c-2fc6-46c4-b609-1d33fce0f60c',
        computer=flexpart_code.computer)

    #builder starts
    workflow = plugins.WorkflowFactory('flexpart.multi_dates')
    builder = workflow.get_builder()
    builder.fcosmo_code = flexpart_code
    builder.fifs_code = orm.load_code('flexpart_ifs@daint')
    builder.check_meteo_ifs_code = orm.load_code('check-ifs-data@daint-direct-106')
    builder.check_meteo_cosmo_code = orm.load_code('check-cosmo-data@daint-direct-106')

    #basic settings
    builder.simulation_dates = simulation_dates
    builder.integration_time = orm.Int(24)
    builder.offline_integration_time = orm.Int(48)

    #meteo realted settings
    builder.model = orm.Str(model)
    builder.model_offline = orm.Str(model_offline)
    
    meteo_path = orm.RemoteData(
            remote_path=scratch_address+model+'/',
            computer = flexpart_code.computer)
    builder.meteo_path = meteo_path
    builder.meteo_inputs = orm.Dict(
        dict=read_yaml_data('inputs/meteo_inputs.yaml', names=[
            model,
        ])[model])

    if model_offline is not None:
        meteo_path_offline = orm.RemoteData(
            remote_path = scratch_address+model_offline,
            computer=flexpart_code.computer)
        builder.meteo_path_offline = meteo_path_offline
        builder.meteo_inputs_offline = orm.Dict(
        dict=read_yaml_data('inputs/meteo_inputs.yaml', names=[
            model_offline,
        ])[model_offline])

    builder.gribdir=orm.Str(scratch_address)
   
    
    #model settings
    builder.command = orm.Dict(
        dict=read_yaml_data('inputs/command.yaml')) #simulation date will be overwritten
    builder.input_phy = orm.Dict(
        dict=read_yaml_data('inputs/input_phy.yaml'))
    builder.locations = orm.Dict(
        dict=read_yaml_data('inputs/locations.yaml', names=[
            'TEST_32',
        ]))
    builder.release_settings = orm.Dict(
        dict=read_yaml_data('inputs/release.yaml'))

    #other
    builder.outgrid = orm.Dict(
        dict=read_yaml_data('inputs/outgrid.yaml', names=[
            'Europe',
        ])['Europe'])
    builder.outgrid_nest = orm.Dict(dict=read_yaml_data(
        'inputs/outgrid_nest.yaml', names=[
            'Europe',
        ])['Europe']) 
    builder.species = species
    builder.land_use = {
        'glc': glc,
        'surfdata': surfdata,
        'surfdepo': surfdepo,
    }
    builder.land_use_ifs = {
        'glc': glc_ifs,
        'surfdata': surfdata,
        'surfdepo': surfdepo,
    }
    builder.parent_calc_folder = parent_folder
    builder.flexpart.metadata.options.stash = {
        'source_list': ['aiida.out', 'grid_time_*.nc'],
        'target_base': f'/store/empa/em05/{username}/aiida_stash',
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