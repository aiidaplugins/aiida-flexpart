#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
import pathlib
import datetime
import yaml
from aiida import orm, plugins, engine, cmdline

def read_yaml_data(data_filename: str, names=None) -> dict:
    """Read in a YAML data file as a dictionary"""
    data_path = pathlib.Path(data_filename)
    try:
        with data_path.open('r', encoding='utf-8') as fp:
            yaml_data = yaml.safe_load(fp)
    except FileNotFoundError:
        raise

    return {key: value for key, value in yaml_data.items() if key in names} if names else yaml_data

# TODO: add range parsing with '--'
def simulation_date_parser(date_string: str) -> list:
    """
    Parse a range of dates and returns a list of date strings.
    
    Examples:
        2021-01-02--2021-01-10 -> [2021-01-02 00:00:00, 2021-01-02 00:00:00, ..., 2021-01-10 00:00:00]
        2021-01-02, 2021-01-10 -> [2021-01-02 00:00:00, 2021-01-10 00:00:00]
        2021-01-02 -> [2021-01-02 00:00:00,]
    """
    if ',' in date_string:
        date_range = [date.strip() + '00:00:00' for date in date_string.split(',')]
    elif '--' in date_string:
        date_start, date_end = list(map(lambda date: datetime.datetime.strptime(date, "%Y-%m-%d"), date_string.split('--')))
        date_range = [date.strftime("%Y-%m-%d 00:00:00") for date in [date_start + datetime.timedelta(days=x) for x in range(0, (date_end-date_start).days+1)]]
    else:
        date_range = [date_string.strip() + '00:00:00']
    
    return orm.List(list=date_range)

def test_run(flexpart_code):
    """Run workflow."""
    # TODO: ask Stephan about meteo data in this range of dates
    simulation_date = simulation_date_parser(["2021-01-02--2021-01-10","2021-01-02"])
    
    # TODO: test workflow with multiple locations
    locations_data = read_yaml_data("locations.yaml", names=["TEST_32",])

    # TODO: should define a variable for the meteo model name
    #   e.g. meteo_model_name = 'cosmo7'
    meteo_inputs = read_yaml_data("meteo_inputs.yaml", names=["cosmo7",])["cosmo7"]

    workflow = plugins.WorkflowFactory("flexpart.multi_dates")
    builder = workflow.get_builder()
    builder.code = flexpart_code
    # TODO: double-check with Stephan about the geo region name
    builder.outgrid = read_yaml_data("outgrid.yaml", names=["Europe",])["Europe"]
    builder.outgrid_nest = read_yaml_data("outgrid_nest.yaml", names=["Europe",])["Europe"] # optional input
    builder.simulation_date = simulation_date
    builder.locations_data = locations_data
    builder.meteo_inputs = meteo_inputs
    
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