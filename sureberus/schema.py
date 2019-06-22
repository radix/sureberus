"""
Utility functions that allow declaring schemas in nicer ways.
"""

from .constants import _marker


def when_tag_is(tag, choices, default_choice=_marker):
    wti = {"tag": tag, "choices": choices}
    if default_choice is not _marker:
        wti["default_choice"] = default_choice
    return {"when_tag_is": wti}


def when_key_is(key, choices, default_choice=_marker):
    wki = {"key": key, "choices": choices}
    if default_choice is not _marker:
        wki["default_choice"] = default_choice
    return {"when_key_is": wki}


def when_key_exists(choices):
    return {"when_key_exists": choices}


def mk(d, kw, **morekw):
    schema = {}
    if d is not None:
        schema.update(d)
    schema.update(kw)
    schema.update(morekw)
    return schema


def Dict(required=True, anyof=None, schema=None, **kwargs):
    if schema is not None:
        kwargs["schema"] = schema
    if anyof is not None:
        kwargs["anyof"] = anyof
    return mk(None, kwargs, type="dict", required=required)


class _MISSING(object):
    pass


def DictWhenKeyIs(key, choices, default_choice=_MISSING, **kwargs):
    """
    Deprecated. Pass `chooose_schema=when_key_is(...)` to `Dict`.
    """
    when_key_is = {"key": key, "choices": choices}
    if default_choice is not _MISSING:
        when_key_is["default_choice"] = default_choice
    return Dict(when_key_is=when_key_is, **kwargs)


def DictWhenKeyExists(choices, **kwargs):
    """
    Deprecated. Pass `chooose_schema=when_key_exists(...)` to `Dict`.
    """
    return Dict(when_key_exists=choices, **kwargs)


def SubSchema(_d=None, **kwargs):
    return {"schema": mk(_d, kwargs)}


def String(required=True, **kwargs):
    return mk(None, kwargs, type="string", required=required)


def Integer(required=True, **kwargs):
    return mk(None, kwargs, type="integer", required=required)


def Float(required=True, **kwargs):
    return mk(None, kwargs, type="float", required=required)


def Number(required=True, **kwargs):
    return mk(None, kwargs, type="number", required=required)


def Boolean(required=True, **kwargs):
    return mk(None, kwargs, type="boolean", required=required)


def List(required=True, _d=None, **kwargs):
    return mk(_d, kwargs, type="list", required=required)
