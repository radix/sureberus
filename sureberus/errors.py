import attr


class SchemaError(Exception):
    def __str__(self):
        return self.fmt.format(**self.format_fields())

    def format_fields(self):
        return self.__dict__


class SureError(Exception):
    def __str__(self):
        stack = "root"
        stack += "".join("[{!r}]".format(el) for el in self.stack)
        return "<At {stack}: {msg}>".format(
            stack=stack, msg=self.fmt.format(**self.format_fields())
        )

    def format_fields(self):
        return self.__dict__


@attr.s
class DictFieldNotFound(SureError):
    fmt = "Can't find required field {key} in dict {value}"
    key = attr.ib()
    value = attr.ib()
    stack = attr.ib()


@attr.s
class ExpectedOneField(SureError):
    fmt = "One of the following fields must be defined: {expected} in {value!r}"
    expected = attr.ib()
    value = attr.ib()
    stack = attr.ib()


@attr.s
class BadType(SureError):
    fmt = "{value!r} must be of {type_} type"
    value = attr.ib()
    type_ = attr.ib()
    stack = attr.ib()


@attr.s
class NoneMatched(SureError):
    fmt = "None of the schemas matched {value!r}:\n{errors}"
    value = attr.ib()
    errors = attr.ib()
    stack = attr.ib()

    def format_fields(self):
        errors = []
        for error in self.errors:
            errors.append("  * Error: {}".format(error))
        fields = self.__dict__.copy()
        fields["errors"] = "\n".join(errors)
        return fields


@attr.s
class MoreThanOneMatched(SureError):
    fmt = "More than one schema matched {value!r} in a `oneof` rule: {matched}"
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
    fmt = "Value {value!r} is not allowed. Must be on of {values!r}"
    value = attr.ib()
    values = attr.ib()
    stack = attr.ib()


@attr.s
class MaxLengthExceeded(SureError):
    fmt = "Value {value!r} is greater than max length of {length}"
    value = attr.ib()
    length = attr.ib()
    stack = attr.ib()


@attr.s
class DisallowedField(SureError):
    fmt = "Because {field!r} is defined, {excluded!r} must not be present"
    field = attr.ib()
    excluded = attr.ib()
    stack = attr.ib()


@attr.s
class CustomValidatorError(SureError):
    fmt = "Custom validator failed for {field}: {msg}"
    field = attr.ib()
    msg = attr.ib()
    stack = attr.ib()


@attr.s
class OutOfBounds(SureError):
    fmt = "Number {number!r} is out of bounds, must be at least {min} and at most {max}"
    number = attr.ib()
    min = attr.ib()
    max = attr.ib()
    stack = attr.ib()


@attr.s
class DefaultSetterUnexpectedError(SureError):
    fmt = "default setter raised an exception for key {key!r} and value {value!r}. Exception: {exception}"
    key = attr.ib()
    value = attr.ib()
    exception = attr.ib()
    stack = attr.ib()

    def format_fields(self):
        fields = self.__dict__.copy()
        fields["exception"] = "{}: {}".format(
            type(self.exception).__name__, self.exception
        )
        return fields


@attr.s
class ValidatorUnexpectedError(SureError):
    fmt = "validator for field {field!r} failed with value {value!r}. Exception: {exception}"
    field = attr.ib()
    value = attr.ib()
    exception = attr.ib()
    stack = attr.ib()

    def format_fields(self):
        fields = self.__dict__.copy()
        fields["exception"] = "{}: {}".format(
            type(self.exception).__name__, self.exception
        )
        return fields


@attr.s
class CoerceUnexpectedError(SureError):
    fmt = "coerce failed with value {value!r}. Exception: {exception}"
    value = attr.ib()
    exception = attr.ib()
    stack = attr.ib()

    def format_fields(self):
        fields = self.__dict__.copy()
        fields["exception"] = "{}: {}".format(
            type(self.exception).__name__, self.exception
        )
        return fields


@attr.s
class UnknownSchemaDirectives(SchemaError):
    fmt = "Unknown schema directives {directives!r}"
    directives = attr.ib()
