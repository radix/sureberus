import attr


marker = object()


def normalize_dict(dict_schema, value, stack=()):
    new_dict = {}
    for key, key_schema in dict_schema.iteritems():
        if key not in value:
            default = key_schema.get('default', marker)
            if default is not marker:
                new_value = default
            else:
                raise DictFieldNotFound(key, value=value, stack=stack)
        else:
            new_value = normalize_schema(key_schema, value[key], stack=stack + (key,))
        new_dict[key] = new_value
    return new_dict


def normalize_schema(schema, value, stack):
    type_ = schema.get('type', None)
    if type_ is None:
        return value
    elif type_ == 'integer':
        if not isinstance(value, int):
            raise BadType(value, type_, stack)
        else:
            return value
    elif type_ == 'dict':
        if not isinstance(value, dict):
            raise BadType(value, type_, stack)
        else:
            return normalize_dict(schema['schema'], value, stack)


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
