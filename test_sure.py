import pytest

from sureberus import normalize_dict, normalize_schema, DictFieldNotFound, BadType


id_int = {'id': {'type': 'integer'}}
nested_num_int = {'nested': {'type': 'dict', 'schema': {'num': {'type': 'integer'}}}}
default_num = {'num': {'type': 'integer', 'default': 0}}


def test_sure():
    sample = {'id': 3}
    assert normalize_dict(id_int, sample) == sample

def test_bad_type():
    sample = {'id': '3'}
    with pytest.raises(BadType) as ei:
        normalize_dict(id_int, sample)
    assert ei.value.value == '3'
    assert ei.value.type_ == 'integer'
    assert ei.value.stack == ('id',)

def test_field_not_found():
    with pytest.raises(DictFieldNotFound) as ei:
        normalize_dict(id_int, {'foo': 'bar'})
    assert ei.value.key == 'id'
    assert ei.value.value == {'foo': 'bar'}
    assert ei.value.stack == ()

def test_nested_error():
    with pytest.raises(BadType) as ei:
        normalize_dict(nested_num_int, {'nested': {'num': 'three!'}})
    assert ei.value.value == 'three!'
    assert ei.value.type_ == 'integer'
    assert ei.value.stack == ('nested', 'num')

def test_default():
    old_dict = {}
    new_dict = normalize_dict(default_num, old_dict)
    assert old_dict == {}
    assert new_dict == {'num': 0}
