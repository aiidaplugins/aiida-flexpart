#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ifs example run"""

import pathlib
import click
import yaml
import aiida
from aiida import cmdline, engine, orm, plugins, common
from aiida.orm import QueryBuilder, RemoteStashFolderData, Dict,List,RemoteData,load_node
aiida.load_profile()
query_dict = {'path': [{
        'cls': RemoteStashFolderData,
        'tag': 'remote',
    }],
    'project': {
        'remote': ['uuid', '*']
    }
}
qb = QueryBuilder.from_dict(query_dict)

remotes = {'a':a[1] for a in qb.all()[:1]}
print(remotes)

# Set up calculation.
calc = plugins.CalculationFactory('new.post')
builder = calc.get_builder()
builder.code = orm.load_code('test_code@localhost')
builder.remote = remotes
engine.run(builder)
  
