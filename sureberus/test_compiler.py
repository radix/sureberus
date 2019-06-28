import pytest


from .compiler import compile
from .instructions import AddToSchemaRegistry, CheckAllowList, CheckField, CheckType, FieldTransformer, Transformer
from . import schema as S
from .constants import _marker


def test_type():
    assert compile({"type": "integer"}) == Transformer([CheckType("integer")])


def test_two_things():
    assert compile({"type": "integer", "allowed": [3, 2, 1]}) == Transformer([
        CheckAllowList([3, 2, 1]),
        CheckType("integer"),
    ])


def test_compile_schema_registry():
    """The schemas inside of a registry are compiled to instructions as well"""
    schema = {"registry": {"foo": S.Integer()}}
    assert compile(schema) == Transformer([
        AddToSchemaRegistry(schemas={"foo": Transformer([CheckType("integer")])})
    ])


def test_compile_fields():
    schema = S.Dict(fields=dict(field=S.Integer()))
    assert compile(schema) == Transformer([
        CheckField("field", FieldTransformer([CheckType("integer")], required=True, default=_marker, rename=None)),
        CheckType("dict"),
    ])
