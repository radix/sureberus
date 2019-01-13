"""
Utility functions that allow declaring schemas in nicer ways.
"""


def mk(d, kw, **morekw):
    schema = {}
    if d is not None:
        schema.update(d)
    schema.update(kw)
    schema.update(morekw)
    return schema


def Dict(required=True, anyof=None, schema={}):
    kw = {}
    if anyof is not None:
        kw['anyof'] = anyof
    return mk(None, kw, type='dict', schema=schema, required=required)

def SubSchema(_d=None, **kwargs):
    return {'schema': mk(_d, kwargs)}

def String(required=True, **kwargs):
    return mk(None, kwargs, type='string', required=required)

def Integer(required=True, **kwargs):
    return mk(None, kwargs, type='integer', required=required)

def Boolean(required=True, **kwargs):
    return mk(None, kwargs, type='boolean', required=required)

def List(required=True, _d=None, **kwargs):
    return mk(_d, kwargs, type='list', required=required)
