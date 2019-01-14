import pytest

from sureberus import normalize_dict, normalize_schema
from sureberus import schema as S
from sureberus import errors as E


id_int = {'id': S.Integer()}

def test_dict_of_int():
    sample = {'id': 3}
    assert normalize_dict(id_int, sample) == sample

def test_bad_type():
    sample = {'id': '3'}
    with pytest.raises(E.BadType) as ei:
        normalize_dict(id_int, sample)
    assert ei.value.value == '3'
    assert ei.value.type_ == 'integer'
    assert ei.value.stack == ('id',)

def test_field_not_found():
    with pytest.raises(E.DictFieldNotFound) as ei:
        normalize_dict({'id': S.Integer(required=True)}, {})
    assert ei.value.key == 'id'
    assert ei.value.value == {}
    assert ei.value.stack == ()

def test_not_required():
    assert normalize_dict({'id': S.Integer(required=False)}, {}) == {}

def test_allow_unknown():
    assert normalize_dict(id_int, {'id': 3, 'foo': 'bar'}, allow_unknown=True) == {'id': 3, 'foo': 'bar'}

def test_disallow_unknown():
    with pytest.raises(E.UnknownFields) as ei:
        normalize_dict(id_int, {'id': 3, 'foo': 'bar'}, allow_unknown=False)

def test_disallow_unknown_in_normalize_schema():
    with pytest.raises(E.UnknownFields) as ei:
        normalize_schema(S.Dict(schema=id_int), {'id': 3, 'foo': 'bar'}, allow_unknown=False)

def test_allow_unknown_in_dict_schema():
    schema = S.Dict(allow_unknown=True, schema={})
    assert normalize_schema(schema, {'x': 'y'}, allow_unknown=False) == {'x': 'y'}

def test_allow_unknown_in_list_schema():
    schema = S.List(allow_unknown=True, schema=S.Dict(schema={'x': S.String()}))
    val = [{'x': 'y', 'extra': 0}]
    assert normalize_schema(schema, val, allow_unknown=False) == val

def test_allow_unknown_in_anyof_schema():
    schema = S.Dict(
        allow_unknown=True,
        anyof=[S.SubSchema(x=S.String()), S.SubSchema(y=S.String())]
    )
    val = {'x': 'foo', 'extra': 'bar'}
    normalize_schema(schema, val, allow_unknown=False) == val

def test_bool():
    normalize_schema(S.Boolean(), True)
    with pytest.raises(E.BadType) as ei:
        normalize_schema(S.Boolean(), 'foo')

def test_float():
    assert normalize_schema(S.Float(), 3.0) == 3.0
    with pytest.raises(E.BadType):
        normalize_schema(S.Float(), 'foo')

def test_float_allows_int():
    """
    Cerberus documentation apparently lies about 'float' only allowing floats --
    it also allows integers.
    """
    assert normalize_schema(S.Float(), 3) == 3

def test_min_max():
    schema = S.Float(min=2.1, max=3.9)
    assert normalize_schema(schema, 3) == 3
    assert normalize_schema(schema, 2.1) == 2.1
    assert normalize_schema(schema, 3.9) == 3.9
    with pytest.raises(E.OutOfBounds) as ei:
        normalize_schema(schema, 2.0)
    assert ei.value.number == 2.0
    assert ei.value.min == 2.1
    assert ei.value.max == 3.9

    with pytest.raises(E.OutOfBounds) as ei:
        normalize_schema(schema, 4)
    assert ei.value.number == 4
    assert ei.value.min == 2.1
    assert ei.value.max == 3.9


def test_number():
    assert normalize_schema(S.Number(), 3.0) == 3.0
    assert normalize_schema(S.Number(), 3) == 3
    with pytest.raises(E.BadType):
        normalize_schema(S.Number(), 'foo')

def test_nested_error():
    schema = {'nested': S.Dict(schema={'num': S.Integer()})}
    with pytest.raises(E.BadType) as ei:
        normalize_dict(schema, {'nested': {'num': 'three!'}})
    assert ei.value.value == 'three!'
    assert ei.value.type_ == 'integer'
    assert ei.value.stack == ('nested', 'num')

def test_default():
    old_dict = {}
    schema = {'num': S.Integer(default=0)}
    new_dict = normalize_dict(schema, old_dict)
    assert old_dict == {}
    assert new_dict == {'num': 0}

def test_default_setter():
    old_dict = {'foo': 0}
    schema = {
        'foo': S.Integer(),
        'foo-incremented': {'default_setter': lambda doc: doc['foo'] + 1}
    }
    new_dict = normalize_dict(schema, old_dict)
    assert old_dict == {'foo': 0}
    assert new_dict == {'foo': 0, 'foo-incremented': 1}


def test_normalize_schema():
    assert normalize_schema(S.Integer(), 3)

def test_anyof():
    anyof = {'anyof': [S.Integer(), S.String()]}
    assert normalize_schema(anyof, 3) == 3
    assert normalize_schema(anyof, 'three') == 'three'
    with pytest.raises(E.NoneMatched) as ei:
        normalize_schema(anyof, object())

def test_anyof_with_normalization():
    """THIS IS THE WHOLE REASON FOR SUREBERUS TO EXIST"""
    # We want to support
    # ANY OF:
    # - {'image': str, 'opacity': {'type': 'integer', 'default': 100}}
    # - {'gradient': ...}

    # And when you normalize this, you actually get the `default` applied in the
    # result, if that rule matches!
    anyof = S.Dict(
        anyof=[
            S.SubSchema(gradient=S.String()),
            S.SubSchema(image=S.String(), opacity=S.Integer(default=100))
        ]
    )

    gfoo = {'gradient': 'foo'}
    assert normalize_schema(anyof, gfoo) == gfoo
    ifoo_with_opacity = {'image': 'foo', 'opacity': 99}
    assert normalize_schema(anyof, ifoo_with_opacity) == ifoo_with_opacity
    ifoo_with_default = {'image': 'foo'}
    assert normalize_schema(anyof, ifoo_with_default) == {'image': 'foo', 'opacity': 100}

def test_nullable_with_anyof():
    """This is the second reason that sureberus exists."""
    anyof = {
        'nullable': True,
        'anyof': [S.Integer(), S.String()],
    }
    assert normalize_schema(anyof, None) == None

def test_oneof():
    oneof = {'oneof': [S.Integer(), S.String()]}
    assert normalize_schema(oneof, 3) == 3
    assert normalize_schema(oneof, 'three') == 'three'
    with pytest.raises(E.NoneMatched) as ei:
        normalize_schema(oneof, object())

def test_oneof_only_one():
    oneof = {'oneof': [{'maxlength': 3}, S.List()]}
    with pytest.raises(E.MoreThanOneMatched) as ei:
        normalize_schema(oneof, [0])

def test_regex():
    schema = S.String(regex=r'\d+')
    assert normalize_schema(schema, '3000') == '3000'
    with pytest.raises(E.RegexMismatch) as ei:
        normalize_schema(schema, 'foo')
    assert ei.value.value == 'foo'
    assert ei.value.regex == r'\d+'

def test_regex_non_string():
    """regex fields on schemas applied to non-strings are ignored"""
    assert normalize_schema({'regex': r'\d+'}, 3) == 3

def test_maxlength():
    with pytest.raises(E.MaxLengthExceeded):
        normalize_schema({'maxlength': 3}, 'foob')

    with pytest.raises(E.MaxLengthExceeded):
        normalize_schema({'maxlength': 3}, [0,1,2,3])

def test_list():
    schema = S.List()
    val = [1, 'two', object()]
    assert normalize_schema(schema, val) == val

def test_list_schema():
    schema = S.List(schema=S.Integer())
    val = [1, 2, 3]
    assert normalize_schema(schema, val) == val

    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, [1, 'two', object()])
    assert ei.value.value == 'two'
    assert ei.value.stack == (1,)

def test_list_schema_without_type():
    # This is really stupid, but cerberus allows it
    schema = {'schema': {'type': 'integer'}}
    assert normalize_schema(schema, [33]) == [33]
    # Calling normalize_schema(schema, {}) will throw an internal error :(

def test_dict_schema_without_type():
    schema = {'schema': {'x': {'type': 'integer'}}}
    assert normalize_schema(schema, {'x': 33}) == {'x': 33}

def test_list_normalize():
    schema = S.List(schema=S.Dict(schema={'x': S.String(default='')}))
    result = normalize_schema(schema, [{}])
    assert result == [{'x': ''}]

def test_allowed():
    schema = S.String(allowed=['2', '3'])
    assert normalize_schema(schema, '3') == '3'
    with pytest.raises(E.DisallowedValue) as ei:
        normalize_schema(schema, '4')

def test_excludes():
    schema = S.Dict(schema={'x': S.String(excludes=['other'])})
    with pytest.raises(E.DisallowedField) as ei:
        normalize_schema(schema, {'x': 'foo', 'other': 'bar'}, allow_unknown=True)

def test_excludes_single():
    schema = S.Dict(schema={'x': S.String(excludes='other')})
    with pytest.raises(E.DisallowedField) as ei:
        normalize_schema(schema, {'x': 'foo', 'other': 'bar'}, allow_unknown=True)

def test_excludes_only_if_exists():
    schema = S.Dict(allow_unknown=True, schema={'this': S.String(required=False, excludes='other')})
    assert normalize_schema(schema, {'other': 'foo'}) == {'other': 'foo'}

def test_coerce():
    def _to_list(item):
        if isinstance(item, list):
            return item
        else:
            return [item]
    schema = {'coerce': _to_list}
    assert normalize_schema(schema, 33) == [33]

def test_validator():
    called = []
    def val(field, value, error):
        called.append((field, value, error))
    schema = {'key': {'validator': val}}
    assert normalize_dict(schema, {'key': 'hi'}) == {'key': 'hi'}
    assert len(called) == 1
    assert called[0][0] == 'key'
    assert called[0][1] == 'hi'

def test_validator_error():
    def val(field, value, error):
        error(field, "heyo")
    schema = {'key': {'validator': val}}
    with pytest.raises(E.CustomValidatorError) as ei:
        assert normalize_dict(schema, {'key': 'hi'}) == {'key': 'hi'}
    assert ei.value.field == 'key'
    assert ei.value.msg == 'heyo'

def test_default_setter_in_starof():
    """If a default setter raises inside of a *of-rule, it is treated as the
    rule not validating
    """
    called = []
    def blow_up(x):
        called.append(True)
        1 / 0
    anyof = {
        'allow_unknown': True,
        'anyof': [
            S.Dict(required=False, schema={'foo': S.String(required=False, default_setter=blow_up)}),
            S.Dict(required=False, schema={'bar': S.String(required=False)}),
        ]
    }
    assert normalize_schema(anyof, {'bar': 'baz'}) == {'bar': 'baz'}
    assert called == [True]

def test_default_setter_raises():
    """If a default_setter raises, it is wrapped in a DefaultSetterUnexpectedError."""
    schema = S.Dict(schema={'key': S.String(required=False, default_setter=lambda x: 1 / 0)})
    with pytest.raises(E.DefaultSetterUnexpectedError) as ei:
        normalize_schema(schema, {})
    assert ei.value.key == 'key'
    assert ei.value.value == {}
    assert type(ei.value.exception) == ZeroDivisionError

def test_validator_raises():
    """If a validator raises, it is wrapped in a ValidatorUnexpectedError."""
    schema = S.Dict(schema={'key': S.String(required=False, validator=lambda f, v, e: 1 / 0)})
    with pytest.raises(E.ValidatorUnexpectedError) as ei:
        normalize_schema(schema, {'key': 'hello'})
    assert ei.value.field == 'key'
    assert ei.value.value == 'hello'
    assert type(ei.value.exception) == ZeroDivisionError

def test_coerce_raises():
    """If a coerce raises, it is wrapped in a CoerceUnexpectedError."""
    schema = S.Dict(schema={'key': S.String(required=False, coerce=lambda x: 1 / 0)})
    with pytest.raises(E.CoerceUnexpectedError) as ei:
        normalize_schema(schema, {'key': 'hello'})
    assert ei.value.value == 'hello'
    assert type(ei.value.exception) == ZeroDivisionError
