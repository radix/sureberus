import attr


class SureError(Exception):
    def __str__(self):
        stack = 'root'
        stack += ''.join('[{!r}]'.format(el) for el in self.stack)
        return "<At {stack}: {msg}>".format(
            stack=stack,
            msg=self.fmt.format(**self.__dict__))

@attr.s
class DictFieldNotFound(SureError):
    fmt = 'required field {key} in dict {value}'
    key = attr.ib()
    value = attr.ib()
    stack = attr.ib()

@attr.s
class BadType(SureError):
    fmt = '{value!r} must be of {type_} type'
    value = attr.ib()
    type_ = attr.ib()
    stack = attr.ib()

@attr.s
class NoneMatched(SureError):
    fmt = 'None of the following schemas matched {value!r}: {schemas}'
    value = attr.ib()
    schemas = attr.ib()
    stack = attr.ib()

@attr.s
class MoreThanOneMatched(SureError):
    fmt = 'More than one schema matched {value!r} in a `oneof` rule: {matched}'
    value = attr.ib()
    matched = attr.ib()
    stack = attr.ib()

@attr.s
class RegexMismatch(SureError):
    fmt = "value does not match regex {value!r} {regex!r}"
    value = attr.ib()
    regex = attr.ib()
    stack = attr.ib()

@attr.s
class UnknownFields(SureError):
    fmt = "Dict {value!r} had unknown fields: {fields!r}"
    value = attr.ib()
    fields = attr.ib()
    stack = attr.ib()

@attr.s
class DisallowedValue(SureError):
    fmt = 'Value {value!r} is not allowed. Must be on of {values!r}'
    value = attr.ib()
    values = attr.ib()
    stack = attr.ib()

@attr.s
class MaxLengthExceeded(SureError):
    fmt = 'Value {value!r} is greater than max length of {length}'
    value = attr.ib()
    length = attr.ib()
    stack = attr.ib()

@attr.s
class DisallowedField(SureError):
    fmt = 'Because {field} is defined, the following fields must be excluded: {excluded}'
    field = attr.ib()
    excluded = attr.ib()
    stack = attr.ib()

@attr.s
class CustomValidatorError(SureError):
    fmt = 'Custom validator failed for {field}: {msg}'
    field = attr.ib()
    msg = attr.ib()
    stack = attr.ib()

@attr.s
class OutOfBounds(SureError):
    fmt = 'Number {number!r} is out of bounds, must be at least {min} and at most {max}'
    number = attr.ib()
    min = attr.ib()
    max = attr.ib()
    stack = attr.ib()
