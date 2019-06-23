import pytest

from .interpreter import interpret
from .instructions import CheckType
from . import INIT_CONTEXT
from . import errors as E

def test_check_type():
    ins = [CheckType("integer")]
    assert interpret(ins, 3, INIT_CONTEXT) == 3
    with pytest.raises(E.BadType):
        interpret(ins, "foo", INIT_CONTEXT)

