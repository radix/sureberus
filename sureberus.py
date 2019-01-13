from __future__ import print_function

from copy import deepcopy

import attr


def normalize_dict(dict_schema, value, stack=()):
    new_dict = {}
    for key, key_schema in dict_schema.iteritems():
        if key not in value:
            default = key_schema.get('default', _marker)
            if default is not _marker:
                new_value = default
            else:
                raise DictFieldNotFound(key, value=value, stack=stack)
        else:
            new_value = normalize_schema(key_schema, value[key], stack=stack + (key,))
        new_dict[key] = new_value
    return new_dict

_marker = object()

TYPES = {
    'integer': int,
    'dict': dict,
    'string': str,
}

def normalize_schema(schema, value, stack=()):
    if value is None and schema.get('nullable', False):
        return value

    if 'type' in schema:
        check_type(schema, value, stack)

    if 'anyof' in schema:
        clone = deepcopy(value)
        errors = []
        for subrule in schema['anyof']:
            cloned_schema = deepcopy(schema)
            # XXX: this is not very principled
            del cloned_schema['anyof']
            cloned_schema.update(subrule)
            subrule = cloned_schema
            try:
                   subresult = normalize_schema(subrule, clone, stack)
            except NiceError as e:
                   errors.append(e)
            else:
                return subresult
        raise NoneMatched(clone, schema['anyof'], stack)

    if schema.get('type', None) == 'dict' and 'schema' in schema:
        return normalize_dict(schema['schema'], value, stack)

    return value


def check_type(schema, value, stack):
    type_ = schema['type']
    types = TYPES[type_]
    if not isinstance(value, types):
        raise BadType(value, type_, stack)


class NiceError(Exception):
    def __str__(self):
        stack = 'root'
        stack += ''.join('[{!r}]'.format(el) for el in self.stack)
        return "<At {stack}: {msg}>".format(
            stack=stack,
            msg=self.fmt.format(**self.__dict__))

@attr.s
class DictFieldNotFound(NiceError):
    fmt = 'Key {key} not in dict {value}'
    key = attr.ib()
    value = attr.ib()
    stack = attr.ib()

@attr.s
class BadType(NiceError):
    fmt = 'Wanted type {type_}, got {value}'
    value = attr.ib()
    type_ = attr.ib()
    stack = attr.ib()

@attr.s
class NoneMatched(NiceError):
    fmt = 'None of the following schemas matched {value}: {schemas}'
    value = attr.ib()
    schemas = attr.ib()
    stack = attr.ib()
