import pytest


from .compiler import compile
from .instructions import AddToSchemaRegistry, CheckAllowList, CheckFields, CheckType
from . import schema as S


def test_type():
    assert compile({"type": "integer"}) == [CheckType("integer")]


def test_two_things():
    assert compile({"type": "integer", "allowed": [3, 2, 1]}) == [
        CheckType("integer"),
        CheckAllowList([3, 2, 1]),
    ]


def test_compile_schema_registry():
    """The schemas inside of a registry are compiled to instructions as well"""
    schema = {"registry": {"foo": S.Integer()}}
    assert compile(schema) == [
        AddToSchemaRegistry(schemas={"foo": [CheckType("integer")]})
    ]


def test_compile_fields():
    schema = S.Dict(fields=dict(field=S.Integer()))
    assert compile(schema) == [
        CheckType("dict"),
        CheckFields({"field": [CheckType("integer")]}),
    ]
