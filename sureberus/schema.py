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


def Dict(_d=None, **kwargs):
    return mk(_d, kwargs, type='dict')

def SubSchema(_d=None, **kwargs):
    return {'schema': mk(_d, kwargs)}

def String(**kwargs):
    return mk(None, kwargs, type='string')

def Integer(**kwargs):
    return mk(None, kwargs, type='integer')

def Boolean(**kwargs):
    return mk(None, kwargs, type='boolean')
