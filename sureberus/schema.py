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


def Dict(anyof=None, schema={}):
    kw = {}
    if anyof is not None:
        kw['anyof'] = anyof
    return mk(None, kw, type='dict', schema=schema)

def SubSchema(_d=None, **kwargs):
    return {'schema': mk(_d, kwargs)}

def String(**kwargs):
    return mk(None, kwargs, type='string')

def Integer(**kwargs):
    return mk(None, kwargs, type='integer')

def Boolean(**kwargs):
    return mk(None, kwargs, type='boolean')

def List(_d=None, **kwargs):
    return mk(_d, kwargs, type='list')
