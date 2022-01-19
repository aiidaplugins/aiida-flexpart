#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
from aiida import orm, plugins, engine, cmdline

def test_run(flexpart_code):
    """Run workflow."""
    simulation_date = orm.Str('2021-01-02 00:00:00')
    wf = plugins.WorkflowFactory('flexpart.multi_dates')
    builder = wf.get_builder()
    builder.code = flexpart_code
    builder.simulation_date = simulation_date
    
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