from __future__ import print_function

from copy import deepcopy
import re

import attr
import six

from . import errors as E

__all__ = ['normalize_dict', 'normalize_schema']


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
    for key, key_schema in dict_schema.items():
        if key not in value:
            replacement = _get_default(key, key_schema, value, ctx)
            if replacement is not _marker:
                new_dict[key] = replacement
            elif key_schema.get('required', False) == True:
                raise E.DictFieldNotFound(key, value=value, stack=ctx.stack)
        if key in value:
            new_dict[key] = _normalize_schema(key_schema, value[key], ctx.push_stack(key))
        for excluded_field in key_schema.get('excludes', ()):
            if excluded_field in value:
                raise E.DisallowedField(key, key_schema['excludes'], ctx.stack)
    return new_dict

def _get_default(key, key_schema, doc, ctx):
    default = key_schema.get('default', _marker)
    if default is not _marker:
        return default
    else:
        default_setter = key_schema.get('default_setter', None)
        if default_setter is not None:
            print("default setter")
            try:
                return default_setter(doc)
            except Exception as e:
                raise E.DefaultSetterUnexpectedError(key, key_schema, doc, e, ctx.stack)
    return _marker

_marker = object()

TYPES = {
    'none': type(None),
    'integer': six.integer_types,
    'float': (float,) + six.integer_types, # cerberus documentation lies -- float also includes ints.
    'number': (float,) + six.integer_types,
    'dict': dict,
    'list': list,
    'string': six.string_types,
    'boolean': bool,
}

def _normalize_schema(schema, value, ctx):
    if 'allow_unknown' in schema:
        ctx = ctx.set_allow_unknown(schema['allow_unknown'])

    if value is None and schema.get('nullable', False):
        return value

    if 'oneof' in schema:
        return _normalize_multi(schema, value, 'oneof', ctx)

    if 'anyof' in schema:
        return _normalize_multi(schema, value, 'anyof', ctx)

    if 'coerce' in schema:
        try:
            value = schema['coerce'](value)
        except E.SureError:
            raise
        except Exception as e:
            raise E.CoerceUnexpectedError(schema, value, e, ctx.stack)


    if 'allowed' in schema:
        if value not in schema['allowed']:
            raise E.DisallowedValue(value, schema['allowed'], ctx.stack)

    if 'type' in schema:
        _check_type(schema, value, ctx.stack)

    if 'maxlength' in schema:
        if len(value) > schema['maxlength']:
            raise E.MaxLengthExceeded(value, schema['maxlength'], ctx.stack)

    if 'min' in schema:
        if value < schema['min']:
            raise E.OutOfBounds(value, schema['min'], schema.get('max'), ctx.stack)
    if 'max' in schema:
        if value > schema['max']:
            raise E.OutOfBounds(value, schema.get('min'), schema['max'], ctx.stack)

    if 'regex' in schema:
        _check_regex(schema['regex'], value, ctx.stack)

    if 'schema' in schema:
        # The meaning of a `schema` key inside a schema changes based on the
        # type of the *value*. e.g., it is possible to define a schema like
        # `{'schema': {'type': 'integer'}}` note that there is no `type`
        # specified along with this schema. So it checks the value at runtime.
        # If it is a list, it validates each element of the list with that
        # sub-schema. If it is a dict, it *tries* to apply the schema directly
        # as the dict-schema, which leads to a runtime error when it tries to
        # interpret the string `integer` as a schema! Welp, bug-for-bug...
        if isinstance(value, list):
            result = []
            for idx, element in enumerate(value):
                result.append(
                    _normalize_schema(schema['schema'], element, ctx.push_stack(idx))
                )
            value = result
        elif isinstance(value, dict):
            value = _normalize_dict(schema['schema'], value, ctx)

    if 'validator' in schema:
        field = ctx.stack[-1] if len(ctx.stack) else None
        def error(f, m):
            raise E.CustomValidatorError(f, m, stack=ctx.stack)
        try:
            schema['validator'](field, value, error)
        except E.SureError:
            raise
        except Exception as e:
            raise E.ValidatorUnexpectedError(field, schema, value, e, ctx.stack)


    return value

def _normalize_multi(schema, value, key, ctx):
    clone = deepcopy(value)
    #errors = []
    results = []
    matched_schemas = []
    for subrule in schema[key]:
        print("[RADIX]", subrule)
        cloned_schema = deepcopy(schema)
        del cloned_schema[key] # This is not very principled...?
        cloned_schema.update(subrule)
        subrule = cloned_schema
        try:
            subresult = _normalize_schema(subrule, clone, ctx)
        except E.SureError as e:
            print("[RADIX] ERROR", e)
            pass
            #errors.append(e)
        else:
            if key == 'oneof':
                results.append(subresult)
                matched_schemas.append(schema[key])
            elif key == 'anyof':
                return subresult
    if not results:
        raise E.NoneMatched(clone, schema[key], ctx.stack)
    elif key == 'oneof' and len(results) > 1:
        raise E.MoreThanOneMatched(clone, matched_schemas, ctx.stack)
    else:
        return results[0]



def _check_type(schema, value, stack):
    type_ = schema['type']
    types = TYPES[type_]
    if not isinstance(value, types):
        raise E.BadType(value, type_, stack)

def _check_regex(regex, value, stack):
    # apparently you can put `regex` even when `type` isn't `string`, and it
    # only actually gets run if the runtime value is a string.
    if isinstance(value, str):
        if not re.match(regex, value):
            raise E.RegexMismatch(value, regex, stack)
