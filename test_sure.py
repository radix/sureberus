from copy import deepcopy

import pytest

from sureberus import normalize_dict, normalize_schema
from sureberus import schema as S
from sureberus import errors as E


id_int = {"id": S.Integer()}


def test_dict_of_int():
    sample = {"id": 3}
    assert normalize_dict(id_int, sample) == sample


def test_valueschema():
    schema = S.Dict(allow_unknown=True, valueschema=S.Integer())
    assert normalize_schema(schema, {"foo": 3, 52: 52}) == {"foo": 3, 52: 52}
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"foo": "3"})
    assert ei.value.stack == ("foo",)


def test_valueschema_normalizes_values():
    schema = S.Dict(allow_unknown=True, valueschema=S.Integer(coerce=int))
    assert normalize_schema(schema, {"foo": 3, 52: "52"}) == {"foo": 3, 52: 52}


def test_keyschema():
    schema = S.Dict(allow_unknown=True, keyschema=S.String())
    assert normalize_schema(schema, {"foo": 3, "bar": None}) == {"foo": 3, "bar": None}
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"foo": 3, 52: "bar"})
    assert ei.value.stack == (52,)


def test_keyschema_normalizes_keys():
    schema = S.Dict(allow_unknown=True, keyschema=S.String(coerce=str))
    assert normalize_schema(schema, {31: 4, 52: 6}) == {"31": 4, "52": 6}


def test_bad_type():
    sample = {"id": "3"}
    with pytest.raises(E.BadType) as ei:
        normalize_dict(id_int, sample)
    assert ei.value.value == "3"
    assert ei.value.type_ == "integer"
    assert ei.value.stack == ("id",)


def test_field_not_found():
    with pytest.raises(E.DictFieldNotFound) as ei:
        normalize_dict({"id": S.Integer(required=True)}, {})
    assert ei.value.key == "id"
    assert ei.value.value == {}
    assert ei.value.stack == ()


def test_not_required():
    assert normalize_dict({"id": S.Integer(required=False)}, {}) == {}


def test_allow_unknown():
    assert normalize_dict(id_int, {"id": 3, "foo": "bar"}, allow_unknown=True) == {
        "id": 3,
        "foo": "bar",
    }


def test_disallow_unknown():
    with pytest.raises(E.UnknownFields) as ei:
        normalize_dict(id_int, {"id": 3, "foo": "bar"}, allow_unknown=False)


def test_disallow_unknown_in_normalize_schema():
    with pytest.raises(E.UnknownFields) as ei:
        normalize_schema(
            S.Dict(schema=id_int), {"id": 3, "foo": "bar"}, allow_unknown=False
        )


def test_allow_unknown_in_dict_schema():
    schema = S.Dict(allow_unknown=True, schema={})
    assert normalize_schema(schema, {"x": "y"}, allow_unknown=False) == {"x": "y"}


def test_allow_unknown_in_list_schema():
    schema = S.List(allow_unknown=True, schema=S.Dict(schema={"x": S.String()}))
    val = [{"x": "y", "extra": 0}]
    assert normalize_schema(schema, val, allow_unknown=False) == val


def test_allow_unknown_in_anyof_schema():
    schema = S.Dict(
        allow_unknown=True, anyof=[S.SubSchema(x=S.String()), S.SubSchema(y=S.String())]
    )
    val = {"x": "foo", "extra": "bar"}
    normalize_schema(schema, val, allow_unknown=False) == val


def test_bool():
    normalize_schema(S.Boolean(), True)
    with pytest.raises(E.BadType) as ei:
        normalize_schema(S.Boolean(), "foo")


def test_float():
    assert normalize_schema(S.Float(), 3.0) == 3.0
    with pytest.raises(E.BadType):
        normalize_schema(S.Float(), "foo")


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
        normalize_schema(S.Number(), "foo")


def test_nested_error():
    schema = {"nested": S.Dict(schema={"num": S.Integer()})}
    with pytest.raises(E.BadType) as ei:
        normalize_dict(schema, {"nested": {"num": "three!"}})
    assert ei.value.value == "three!"
    assert ei.value.type_ == "integer"
    assert ei.value.stack == ("nested", "num")


def test_default():
    old_dict = {}
    schema = {"num": S.Integer(default=0)}
    new_dict = normalize_dict(schema, old_dict)
    assert old_dict == {}
    assert new_dict == {"num": 0}


def test_default_setter():
    old_dict = {"foo": 0}
    schema = S.Dict(
        schema={
            "foo": S.Integer(),
            "foo-incremented": {"default_setter": lambda doc: doc["foo"] + 1},
        }
    )
    new_dict = normalize_schema(schema, old_dict)
    assert old_dict == {"foo": 0}
    assert new_dict == {"foo": 0, "foo-incremented": 1}

    assert normalize_schema(schema, {"foo": 0, "foo-incremented": 5}) == {
        "foo": 0,
        "foo-incremented": 5,
    }


def test_normalize_schema():
    assert normalize_schema(S.Integer(), 3)


def test_anyof():
    anyof = {"anyof": [S.Integer(), S.String()]}
    assert normalize_schema(anyof, 3) == 3
    assert normalize_schema(anyof, "three") == "three"
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
            S.SubSchema(image=S.String(), opacity=S.Integer(default=100)),
        ]
    )

    gfoo = {"gradient": "foo"}
    assert normalize_schema(anyof, gfoo) == gfoo
    ifoo_with_opacity = {"image": "foo", "opacity": 99}
    assert normalize_schema(anyof, ifoo_with_opacity) == ifoo_with_opacity
    ifoo_with_default = {"image": "foo"}
    assert normalize_schema(anyof, ifoo_with_default) == {
        "image": "foo",
        "opacity": 100,
    }


def test_nullable():
    assert normalize_schema({"nullable": True}, None) == None
    assert normalize_schema(S.Integer(nullable=True), None) == None
    with pytest.raises(E.BadType):
        normalize_schema(S.Integer(nullable=False), None)


def test_nullable_with_anyof():
    """This is the second reason that sureberus exists."""
    anyof = {"nullable": True, "anyof": [S.Integer(), S.String()]}
    assert normalize_schema(anyof, None) == None


def test_oneof():
    oneof = {"oneof": [S.Integer(), S.String()]}
    assert normalize_schema(oneof, 3) == 3
    assert normalize_schema(oneof, "three") == "three"
    with pytest.raises(E.NoneMatched) as ei:
        normalize_schema(oneof, object())


def test_oneof_only_one():
    oneof = {"oneof": [{"maxlength": 3}, S.List()]}
    with pytest.raises(E.MoreThanOneMatched) as ei:
        normalize_schema(oneof, [0])


def test_regex():
    schema = S.String(regex=r"\d+")
    assert normalize_schema(schema, "3000") == "3000"
    with pytest.raises(E.RegexMismatch) as ei:
        normalize_schema(schema, "foo")
    assert ei.value.value == "foo"
    assert ei.value.regex == r"\d+"


def test_regex_non_string():
    """regex fields on schemas applied to non-strings are ignored"""
    assert normalize_schema({"regex": r"\d+"}, 3) == 3


def test_maxlength():
    with pytest.raises(E.MaxLengthExceeded):
        normalize_schema({"maxlength": 3}, "foob")

    with pytest.raises(E.MaxLengthExceeded):
        normalize_schema({"maxlength": 3}, [0, 1, 2, 3])


def test_rename():
    schema = S.Dict(schema={"foo": {"rename": "moo"}})
    val = {"foo": 2}
    assert normalize_schema(schema, val) == {"moo": 2}


def test_rename_with_coerce():
    schema = S.Dict(schema={"foo": {"rename": "moo", "coerce": str}})
    val = {"foo": 2}
    assert normalize_schema(schema, val) == {"moo": "2"}


def test_rename_with_default():
    schema = S.Dict(
        schema={"foo": {"rename": "moo", "type": "boolean", "default": True}}
    )
    val = {}
    assert normalize_schema(schema, val) == {"moo": True}

    val = {"foo": False}
    assert normalize_schema(schema, val) == {"moo": False}


def test_rename_with_both_attributes_present():
    schema = S.Dict(
        schema={"foo": {"rename": "moo", "coerce": str}}, allow_unknown=True
    )
    val = {"foo": 1, "moo": 2}
    assert normalize_schema(schema, val) == {"moo": "1"}

    # Yes, we can swap attributes
    schema = S.Dict(
        schema={
            "foo": {"rename": "moo", "coerce": str},
            "moo": {"rename": "foo", "coerce": str},
        },
        allow_unknown=True,
    )
    val = {"foo": 1, "moo": 2}
    assert normalize_schema(schema, val) == {"moo": "1", "foo": "2"}


def test_rename_with_maxlength():
    schema = S.Dict(schema={"foo": {"rename": "moo", "maxlength": 3}})
    val = {"foo": "fooob"}
    with pytest.raises(E.MaxLengthExceeded):
        assert normalize_schema(schema, val)


def test_list():
    schema = S.List()
    val = [1, "two", object()]
    assert normalize_schema(schema, val) == val


def test_list_schema():
    schema = S.List(schema=S.Integer())
    val = [1, 2, 3]
    assert normalize_schema(schema, val) == val

    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, [1, "two", object()])
    assert ei.value.value == "two"
    assert ei.value.stack == (1,)


def test_list_schema_without_type():
    # This is really stupid, but cerberus allows it
    schema = {"schema": {"type": "integer"}}
    assert normalize_schema(schema, [33]) == [33]
    # Calling normalize_schema(schema, {}) will throw an internal error :(


def test_dict_schema_without_type():
    schema = {"schema": {"x": {"type": "integer"}}}
    assert normalize_schema(schema, {"x": 33}) == {"x": 33}


def test_list_normalize():
    schema = S.List(schema=S.Dict(schema={"x": S.String(default="")}))
    result = normalize_schema(schema, [{}])
    assert result == [{"x": ""}]


def test_allowed():
    schema = S.String(allowed=["2", "3"])
    assert normalize_schema(schema, "3") == "3"
    with pytest.raises(E.DisallowedValue) as ei:
        normalize_schema(schema, "4")


def test_excludes():
    schema = S.Dict(schema={"x": S.String(excludes=["other"])})
    with pytest.raises(E.DisallowedField) as ei:
        normalize_schema(schema, {"x": "foo", "other": "bar"}, allow_unknown=True)


def test_excludes_single():
    schema = S.Dict(schema={"x": S.String(excludes="other")})
    with pytest.raises(E.DisallowedField) as ei:
        normalize_schema(schema, {"x": "foo", "other": "bar"}, allow_unknown=True)


def test_excludes_only_if_exists():
    schema = S.Dict(
        allow_unknown=True, schema={"this": S.String(required=False, excludes="other")}
    )
    assert normalize_schema(schema, {"other": "foo"}) == {"other": "foo"}


def test_coerce():
    def _to_list(item):
        if isinstance(item, list):
            return item
        else:
            return [item]

    schema = {"coerce": _to_list}
    assert normalize_schema(schema, 33) == [33]


def test_coerce_post_basic():
    def _to_list(item):
        if isinstance(item, list):
            return item
        else:
            return [item]

    schema = {"coerce_post": _to_list}
    assert normalize_schema(schema, 33) == [33]


def test_coerce_post_after_children():
    def relies_on_child_norm(doc):
        doc["FOO"] = doc["child"]
        return doc

    schema = {
        "type": "dict",
        "schema": {"child": {"default": "cool-default"}},
        "coerce_post": relies_on_child_norm,
    }
    assert normalize_schema(schema, {}) == {
        "FOO": "cool-default",
        "child": "cool-default",
    }


def test_validator():
    called = []

    def val(field, value, error):
        called.append((field, value, error))

    schema = {"key": {"validator": val}}
    assert normalize_dict(schema, {"key": "hi"}) == {"key": "hi"}
    assert len(called) == 1
    assert called[0][0] == "key"
    assert called[0][1] == "hi"


def test_validator_error():
    def val(field, value, error):
        error(field, "heyo")

    schema = {"key": {"validator": val}}
    with pytest.raises(E.CustomValidatorError) as ei:
        assert normalize_dict(schema, {"key": "hi"}) == {"key": "hi"}
    assert ei.value.field == "key"
    assert ei.value.msg == "heyo"


def test_default_setter_in_starof():
    """If a default setter raises inside of a *of-rule, it is treated as the
    rule not validating
    """
    called = []

    def blow_up(x):
        called.append(True)
        1 / 0

    anyof = {
        "allow_unknown": True,
        "anyof": [
            S.Dict(
                required=False,
                schema={"foo": S.String(required=False, default_setter=blow_up)},
            ),
            S.Dict(required=False, schema={"bar": S.String(required=False)}),
        ],
    }
    assert normalize_schema(anyof, {"bar": "baz"}) == {"bar": "baz"}
    assert called == [True]


def test_default_setter_raises():
    """If a default_setter raises, it is wrapped in a DefaultSetterUnexpectedError."""
    schema = S.Dict(
        schema={"key": S.String(required=False, default_setter=lambda x: 1 / 0)}
    )
    with pytest.raises(E.DefaultSetterUnexpectedError) as ei:
        normalize_schema(schema, {})
    assert ei.value.key == "key"
    assert ei.value.value == {}
    assert type(ei.value.exception) == ZeroDivisionError


def test_validator_raises():
    """If a validator raises, it is wrapped in a ValidatorUnexpectedError."""
    schema = S.Dict(
        schema={"key": S.String(required=False, validator=lambda f, v, e: 1 / 0)}
    )
    with pytest.raises(E.ValidatorUnexpectedError) as ei:
        normalize_schema(schema, {"key": "hello"})
    assert ei.value.field == "key"
    assert ei.value.value == "hello"
    assert type(ei.value.exception) == ZeroDivisionError


def test_coerce_raises():
    """If a coerce raises, it is wrapped in a CoerceUnexpectedError."""
    schema = S.Dict(schema={"key": S.String(required=False, coerce=lambda x: 1 / 0)})
    with pytest.raises(E.CoerceUnexpectedError) as ei:
        normalize_schema(schema, {"key": "hello"})
    assert ei.value.value == "hello"
    assert type(ei.value.exception) == ZeroDivisionError


choice_schema = S.DictWhenKeyIs(
    "type",
    {
        "foo": {"schema": {"foo_sibling": S.String()}},
        "bar": {"schema": {"bar_sibling": S.Integer()}},
    },
)


def test_when_key_is():
    v = {"type": "foo", "foo_sibling": "bar"}
    assert normalize_schema(choice_schema, v) == v
    v2 = {"type": "bar", "bar_sibling": 37}
    assert normalize_schema(choice_schema, v2) == v2


def test_when_key_is_unknown():
    with pytest.raises(E.DisallowedValue) as ei:
        normalize_schema(choice_schema, {"type": "baz"})
    assert ei.value.stack == ("type",)


def test_when_key_is_wrong_choice():
    v = {"type": "foo", "bar_sibling": 37}
    with pytest.raises(E.UnknownFields):  # this could as well be E.DictFieldNotFound...
        normalize_schema(choice_schema, v)


def test_when_key_is_other_schema_directives():
    schema = deepcopy(choice_schema)

    def coerce(x):
        x["bar_sibling"] += 1
        return x

    schema["when_key_is"]["choices"]["bar"]["coerce"] = coerce
    v = {"type": "foo", "foo_sibling": "hi"}
    assert normalize_schema(schema, v) == v
    v2 = {"type": "bar", "bar_sibling": 32}
    assert normalize_schema(schema, v2) == {"type": "bar", "bar_sibling": 33}


def test_when_key_is_common_schema():
    schema = deepcopy(choice_schema)
    schema["schema"] = {"common!": S.String()}
    with pytest.raises(E.DictFieldNotFound) as ei:
        v = {"type": "foo", "foo_sibling": "hi"}
        normalize_schema(schema, v)
    assert ei.value.key == "common!"
    with pytest.raises(E.DictFieldNotFound) as ei:
        v = {"type": "bar", "bar_sibling": 3}
        normalize_schema(schema, v)
    assert ei.value.key == "common!"

    v = {"type": "foo", "foo_sibling": "hi", "common!": "yup"}
    assert normalize_schema(schema, v) == v
    v = {"type": "bar", "bar_sibling": 3, "common!": "yup"}
    assert normalize_schema(schema, v) == v


def test_when_key_is_coercions():
    """Coercions happen *before* when_key_is, so they can e.g.
    convert from a non-dict to a dict.
    """
    schema = deepcopy(choice_schema)

    def coerce(value):
        if isinstance(value, str):
            return {"type": "foo", "foo_sibling": value}
        return value

    schema["coerce"] = coerce
    assert normalize_schema(schema, "hello!") == {
        "type": "foo",
        "foo_sibling": "hello!",
    }


def test_when_key_is_type_check():
    with pytest.raises(E.BadType) as ei:
        normalize_schema(choice_schema, "foo")
    assert ei.value.type_ == "dict"
    assert ei.value.value == "foo"


def test_when_key_is_not_found():
    with pytest.raises(E.DictFieldNotFound) as ei:
        normalize_schema(choice_schema, {"foo_sibling": "hello"})
    assert ei.value.key == "type"


def test_when_key_is_default():
    schema = deepcopy(choice_schema)
    schema["when_key_is"]["default_choice"] = "foo"
    assert normalize_schema(schema, {"foo_sibling": "hello"}) == {
        "foo_sibling": "hello"
    }


choice_existence_schema = S.DictWhenKeyExists(
    {
        "image": {"schema": {"image": S.String(), "width": S.Integer()}},
        "pattern": {"schema": {"pattern": S.Dict(), "color": S.String()}},
    }
)


def test_when_key_exists():
    v = {"image": "foo", "width": 3}
    assert normalize_schema(choice_existence_schema, v) == v
    v = {"pattern": {}, "color": "red"}
    assert normalize_schema(choice_existence_schema, v) == v


def test_when_key_exists_wrong_choice():
    v = {"image": "foo", "color": "red"}
    with pytest.raises(E.UnknownFields):  # this could as well be E.DictFieldNotFound...
        normalize_schema(choice_existence_schema, v)


def test_when_key_exists_error_multiple_keys_exist():
    v = {"image": "foo", "width": 3, "pattern": {}, "color": "red"}
    with pytest.raises(E.DisallowedField) as ei:
        normalize_schema(choice_existence_schema, v)
    assert {ei.value.field, ei.value.excluded} == {"image", "pattern"}


def test_when_key_exists_NO_keys_exist():
    v = {"width": 30}
    with pytest.raises(E.ExpectedOneField) as ei:
        normalize_schema(choice_existence_schema, v)
    assert set(ei.value.expected) == {"pattern", "image"}


def test_when_key_exists_other_schema_directives():
    schema = deepcopy(choice_existence_schema)

    def coerce(x):
        x["width"] += 1
        return x

    schema["when_key_exists"]["image"]["coerce"] = coerce

    v = {"pattern": {}, "color": "red"}
    assert normalize_schema(schema, v) == v
    v = {"image": "foo", "width": 3}
    assert normalize_schema(schema, v) == {"image": "foo", "width": 4}


def test_when_key_exists_common_schema():
    schema = deepcopy(choice_existence_schema)
    schema["schema"] = {"common!": S.String()}
    with pytest.raises(E.DictFieldNotFound) as ei:
        v = {"image": "foo", "width": 3}
        normalize_schema(schema, v)
    assert ei.value.key == "common!"
    with pytest.raises(E.DictFieldNotFound) as ei:
        v = {"pattern": {}, "color": "red"}
        normalize_schema(schema, v)
    assert ei.value.key == "common!"

    v = {"image": "foo", "width": 3, "common!": "yup"}
    assert normalize_schema(schema, v) == v
    v = {"pattern": {}, "color": "red", "common!": "yup"}
    assert normalize_schema(schema, v) == v


def test_when_key_exists_coercions():
    """Coercions happen *before* when_key_exists, so they can e.g.
    convert from a non-dict to a dict.
    """
    schema = deepcopy(choice_existence_schema)

    def coerce(value):
        if value in ["red", "green", "blue"]:
            return {"pattern": {}, "color": value}
        return value

    schema["coerce"] = coerce
    assert normalize_schema(schema, "red") == {"pattern": {}, "color": "red"}


def test_when_key_exists_type_check():
    with pytest.raises(E.BadType) as ei:
        normalize_schema(choice_existence_schema, "foo")
    assert ei.value.type_ == "dict"
    assert ei.value.value == "foo"


def test_registry():
    """Schemas can have inline reusable schemas"""
    schema = {
        "registry": {"my cool schema": {"type": "integer"}},
        "type": "dict",
        "schema": {"x": "my cool schema"},
    }
    assert normalize_schema(schema, {"x": 3}) == {"x": 3}


def test_registry_ref_in_list():
    schema = {"registry": {"inty": S.Integer()}, "type": "list", "schema": "inty"}
    assert normalize_schema(schema, [3, 4, 5]) == [3, 4, 5]


def test_recursive_schemas():
    """Schema registries allow for recursive schemas"""
    schema = {
        "registry": {
            "nested list of ints": S.List(
                schema={"anyof": [S.Integer(), "nested list of ints"]}
            )
        },
        "schema_ref": "nested list of ints",
    }
    for v in [[3, 4, 5], [], [[3]], [[3, 4], 5, [6, 7, [8, 9, [10]]]]]:
        assert normalize_schema(schema, v) == v


def test_circular_registry():
    """Schema registries allow for schemas that refer to each other"""
    schema = {
        "registry": {
            "a": S.Dict(schema={"a": "b"}),
            "b": S.Dict(schema={"b": {"anyof": [S.Integer(), "a"]}}),
        },
        "schema_ref": "a",
    }

    for v in [{"a": {"b": 2}}, {"a": {"b": {"a": {"b": 2}}}}]:
        assert normalize_schema(schema, v) == v

    for v in [{"a": {"b": []}}, {"a": {"a": {"a": {"b": 2}}}}]:
        with pytest.raises(Exception):
            normalize_schema(schema, v)


def test_schema_ref_with_differing_requirement():
    """schema_ref allows overriding the required-ness of a field."""
    schema = {
        "registry": {"requiredfield": S.String(required=True)},
        "type": "dict",
        "schema": {
            "non_required": {"schema_ref": "requiredfield", "required": False},
            "required": "requiredfield",
        },
    }
    assert normalize_schema(schema, {"required": "xx"}) == {"required": "xx"}
    assert normalize_schema(schema, {"required": "xx", "non_required": "yy"}) == {
        "required": "xx",
        "non_required": "yy",
    }
    with pytest.raises(E.DictFieldNotFound):
        normalize_schema(schema, {"non_required": "yy"})


def test_schema_ref_with_defaults_and_nullables():
    """schema_ref allows overriding the default and nullable-ness of a field."""
    schema = {
        "registry": {"requiredfield": S.String(required=True)},
        "type": "dict",
        "schema": {
            "non_required": {
                "schema_ref": "requiredfield",
                "default": None,
                "nullable": True,
            }
        },
    }
    assert normalize_schema(schema, {}) == {"non_required": None}


def test_recursive_schemas_inside_when_key_exists():
    schema = S.Dict(
        registry={
            "recursive": S.List(
                schema=S.DictWhenKeyExists(
                    {
                        "g": {"schema": {"g": S.String(), "sts": "recursive"}},
                        "ot": {"schema": {"ot": S.String()}},
                    }
                )
            )
        },
        schema={"ts": "recursive"},
    )
    for v in [
        {"ts": []},
        {"ts": [{"ot": "the thing"}]},
        {"ts": [{"g": "groupname", "sts": []}]},
        {"ts": [{"g": "g1", "sts": [{"ot": "t1"}]}]},
        {
            "ts": [
                {"g": "g1", "sts": [{"ot": "t1"}, {"g": "g2", "sts": [{"ot": "t3"}]}]}
            ]
        },
    ]:
        assert normalize_schema(schema, v) == v


def test_when_key_exists_direct_reference():
    schema = S.DictWhenKeyExists(
        {"key": "ref"}, registry={"ref": S.Dict(schema={"key": S.String()})}
    )
    assert normalize_schema(schema, {"key": "foo"})


def test_when_key_is_direct_reference():
    schema = S.DictWhenKeyIs(
        "type", {"foo": "ref"}, registry={"ref": S.Dict(schema={"key": S.String()})}
    )
    assert normalize_schema(schema, {"type": "foo", "key": "a string"})


def test_contextual_schemas():
    schema = S.Dict(
        hook_context=lambda v, c: c.set_tag("my_tag", v["type"]),
        schema={
            "type": S.String(),
            "otherthing": {
                "choose_schema": lambda v, c: S.Boolean()
                if c.get_tag("my_tag") == "bool"
                else S.String()
            },
        },
    )
    v = {"type": "bool", "otherthing": True}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "bool", "otherthing": "foo"})

    v = {"type": "nope", "otherthing": "fyoo"}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "nope", "otherthing": True})


def test_data_driven_context():
    schema = S.Dict(
        set_tag={"tag_name": "my_tag", "key": "type"},
        schema={
            "type": S.String(),
            "otherthing": {
                "when_tag_is": {
                    "tag": "my_tag",
                    "choices": {"B": S.Boolean(), "S": S.String()},
                }
            },
        },
    )

    v = {"type": "B", "otherthing": True}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "B", "otherthing": "foo"})

    v = {"type": "S", "otherthing": "fyoo"}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "S", "otherthing": True})

def test_set_tag_with_string():
    schema = S.Dict(
        set_tag="type",
        schema={
            "type": S.String(),
            "otherthing": {
                "when_tag_is": {
                    "tag": "type",
                    "choices": {"B": S.Boolean(), "S": S.String()},
                }
            },
        },
    )

    v = {"type": "B", "otherthing": True}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "B", "otherthing": "foo"})

    v = {"type": "S", "otherthing": "fyoo"}
    assert normalize_schema(schema, v) == v
    with pytest.raises(E.BadType) as ei:
        normalize_schema(schema, {"type": "S", "otherthing": True})

