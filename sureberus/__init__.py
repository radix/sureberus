from __future__ import print_function

from copy import deepcopy
import re

import attr

from . import errors as E


@attr.s
class Context(object):
    stack = attr.ib()
    allow_unknown = attr.ib()

    def push_stack(self, x):
        return Context(stack=self.stack + (x,), allow_unknown=self.allow_unknown)

    def set_allow_unknown(self, x):
        return Context(stack=self.stack, allow_unknown=x)

def normalize_dict(dict_schema, value, stack=(), allow_unknown=False):
    ctx = Context(stack=(), allow_unknown=allow_unknown)
    return _normalize_dict(dict_schema, value, ctx)

def normalize_schema(schema, value, stack=(), allow_unknown=False):
    ctx = Context(stack=(), allow_unknown=allow_unknown)
    return _normalize_schema(schema, value, ctx)

def _normalize_dict(dict_schema, value, ctx):
    new_dict = {}
    extra_keys = set(value.keys()) - set(dict_schema.keys())
    if extra_keys:
        if ctx.allow_unknown:
            for k in extra_keys:
                new_dict[k] = value[k]
        else:
            raise E.UnknownFields(value, extra_keys, stack=ctx.stack)
    for key, key_schema in dict_schema.iteritems():
        if key not in value:
            replacement = get_default(key, key_schema, value)
            if replacement is not _marker:
                new_dict[key] = replacement
            elif key_schema.get('required', False) == True:
                raise E.DictFieldNotFound(key, value=value, stack=ctx.stack)
        if key in value:
            new_dict[key] = _normalize_schema(key_schema, value[key], ctx.push_stack(key))
    return new_dict

def get_default(key, key_schema, doc):
    default = key_schema.get('default', _marker)
    if default is not _marker:
        return default
    else:
        default_setter = key_schema.get('default_setter', None)
        if default_setter is not None:
            return default_setter(doc)
    return _marker

_marker = object()

TYPES = {
    'integer': int,
    'dict': dict,
    'list': list,
    'string': str,
    'boolean': bool,
}

def _normalize_schema(schema, value, ctx):
    if 'allow_unknown' in schema:
        ctx = ctx.set_allow_unknown(schema['allow_unknown'])
    if value is None and schema.get('nullable', False):
        return value

    if 'allowed' in schema:
        if value not in schema['allowed']:
            raise E.DisallowedValue(value, values=schema['allowed'])

    if 'type' in schema:
        check_type(schema, value, ctx.stack)

    if 'maxlength' in schema:
        if len(value) > schema['maxlength']:
            raise E.MaxLengthExceeded(value, length=schema['maxlength'])
    if 'regex' in schema:
        check_regex(schema['regex'], value, ctx.stack)

    if 'anyof' in schema:
        clone = deepcopy(value)
        errors = []
        for subrule in schema['anyof']:
            cloned_schema = deepcopy(schema)
            # XXX: deleting `anyof` here is not very principled.
            del cloned_schema['anyof']
            cloned_schema.update(subrule)
            subrule = cloned_schema
            try:
                subresult = _normalize_schema(subrule, clone, ctx)
            except E.NiceError as e:
                errors.append(e)
            else:
                return subresult
        raise E.NoneMatched(clone, schema['anyof'], ctx.stack)

    if schema.get('type', None) == 'dict' and 'schema' in schema:
        return _normalize_dict(schema['schema'], value, ctx)
    elif schema.get('type', None) == 'list' and 'schema' in schema:
        result = []
        for idx, element in enumerate(value):
            result.append(
                _normalize_schema(schema['schema'], element, ctx.push_stack(idx))
            )
        return result

    return value


def check_type(schema, value, stack):
    type_ = schema['type']
    types = TYPES[type_]
    if not isinstance(value, types):
        raise E.BadType(value, type_, stack)

def check_regex(regex, value, stack):
    # apparently you can put `regex` even when `type` isn't `string`, and it
    # only actually gets run if the runtime value is a string.
    if isinstance(value, str):
        if not re.match(regex, value):
            raise E.RegexMismatch(value, regex, stack)
