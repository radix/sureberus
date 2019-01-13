import attr


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
    fmt = 'Wanted type {type_}, got {value!r}'
    value = attr.ib()
    type_ = attr.ib()
    stack = attr.ib()

@attr.s
class NoneMatched(NiceError):
    fmt = 'None of the following schemas matched {value!r}: {schemas}'
    value = attr.ib()
    schemas = attr.ib()
    stack = attr.ib()

@attr.s
class MoreThanOneMatched(NiceError):
    fmt = 'More than one schema matched {value!r} in a `oneof` rule: {matched}'
    value = attr.ib()
    matched = attr.ib()
    stack = attr.ib()

@attr.s
class RegexMismatch(NiceError):
    fmt = "Value {value!r} did not match regex {regex}"
    value = attr.ib()
    regex = attr.ib()
    stack = attr.ib()

@attr.s
class UnknownFields(NiceError):
    fmt = "Dict {value!r} had unknown fields: {fields!r}"
    value = attr.ib()
    fields = attr.ib()
    stack = attr.ib()

@attr.s
class DisallowedValue(NiceError):
    fmt = 'Value {value!r} is not allowed. Must be on of {values!r}'
    value = attr.ib()
    values = attr.ib()
    stack = attr.ib()

@attr.s
class MaxLengthExceeded(NiceError):
    fmt = 'Value {value!r} is greater than max length of {length}'
    value = attr.ib()
    length = attr.ib()
    stack = attr.ib()

@attr.s
class DisallowedField(NiceError):
    fmt = 'Because {field} is defined, the following fields must be excluded: {excluded}'
    field = attr.ib()
    excluded = attr.ib()
    stack = attr.ib()
