#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ifs example run"""
import aiida
from aiida import engine, orm, plugins
from aiida.orm import QueryBuilder, RemoteStashFolderData
aiida.load_profile()

query_dict = {
    'path': [{
        'cls': RemoteStashFolderData,
        'tag': 'remote',
    }],
    'project': {
        'remote': ['uuid', '*']
    }
}
qb = QueryBuilder.from_dict(query_dict)

remotes = {f'a{j}': a[1] for j, a in enumerate(qb.all())}
print(remotes)

# Set up calculation.
calc = plugins.CalculationFactory('new.post')
builder = calc.get_builder()
builder.code = orm.load_code('test_code@localhost')
builder.remote = remotes
engine.run(builder)
