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

def Dict(required=True, anyof=None, schema={}, **kwargs):
    if anyof is not None:
        kwargs['anyof'] = anyof
    return mk(None, kwargs, type='dict', schema=schema, required=required)

def DictWhenKeyIs(key, choices):
    return {'type': 'dict', 'when_key_is': {'key': key, 'choices': choices}}

def DictWhenKeyExists(choices):
    return {'type': 'dict', 'when_key_exists': choices}

def SubSchema(_d=None, **kwargs):
    return {'schema': mk(_d, kwargs)}

def String(required=True, **kwargs):
    return mk(None, kwargs, type='string', required=required)

def Integer(required=True, **kwargs):
    return mk(None, kwargs, type='integer', required=required)

def Float(required=True, **kwargs):
    return mk(None, kwargs, type='float', required=required)

def Number(required=True, **kwargs):
    return mk(None, kwargs, type='number', required=required)

def Boolean(required=True, **kwargs):
    return mk(None, kwargs, type='boolean', required=required)

def List(required=True, _d=None, **kwargs):
    return mk(_d, kwargs, type='list', required=required)
