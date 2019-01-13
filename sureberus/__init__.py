from __future__ import print_function

from copy import deepcopy
import re

from . import errors as E


def normalize_dict(dict_schema, value, stack=()):
    new_dict = {}
    for key, key_schema in dict_schema.iteritems():
        if key not in value:
            default = key_schema.get('default', _marker)
            if default is not _marker:
                new_value = default
            else:
                default_setter = key_schema.get('default_setter', None)
                if default_setter is not None:
                    new_value = default_setter(value)
                else:
                    raise E.DictFieldNotFound(key, value=value, stack=stack)
        else:
            new_value = normalize_schema(key_schema, value[key], stack=stack + (key,))
        new_dict[key] = new_value
    return new_dict

_marker = object()

TYPES = {
    'integer': int,
    'dict': dict,
    'list': list,
    'string': str,
    'boolean': bool,
}

def normalize_schema(schema, value, stack=()):
    if value is None and schema.get('nullable', False):
        return value

    if 'type' in schema:
        check_type(schema, value, stack)

    if 'regex' in schema:
        check_regex(schema['regex'], value, stack)

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
                subresult = normalize_schema(subrule, clone, stack)
            except E.NiceError as e:
                errors.append(e)
            else:
                return subresult
        raise E.NoneMatched(clone, schema['anyof'], stack)

    if schema.get('type', None) == 'dict' and 'schema' in schema:
        return normalize_dict(schema['schema'], value, stack)
    elif schema.get('type', None) == 'list' and 'schema' in schema:
        result = []
        for idx, element in enumerate(value):
            result.append(normalize_schema(schema['schema'], element, stack + (idx,)))
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
