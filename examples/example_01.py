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
    model_settings = SinglefileData(
        file=INPUT_DIR/'COMMAND')
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

    # set up calculation
    inputs = {
        'code': flexpart_code,
        'outgrid': outgrid,
        'outgrid_nest': outgrid_nest,
        'releases': releases,
        'model_settings': model_settings,
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
