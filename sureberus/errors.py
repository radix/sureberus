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
class RegexMismatch(NiceError):
    fmt = "Value {value!r} did not match regex {regex}"
    value = attr.ib()
    regex = attr.ib()
    stack = attr.ib()
