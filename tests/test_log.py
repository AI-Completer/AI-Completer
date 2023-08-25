import logging
import pytest
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aicompleter as ac
from aicompleter import log

def test_logModule():
    # Check if log module is in proper state.
    assert isinstance(log.root, log.Logger)
    assert log.root.name == 'ROOT'

    assert hasattr(log, 'getLogger')
    assert hasattr(log, 'setLevel')
