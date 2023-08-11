import logging
import pytest
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aicompleter as ac
from aicompleter import log

@pytest.mark.run(order=0x00)
@pytest.mark.dependency()
def test_logModule():
    # Check if log module is in proper state.
    assert isinstance(log.root, log.Logger)
    assert log.root.name == 'ROOT'

    assert hasattr(log, 'getLogger')
    assert hasattr(log, 'setLevel')

@pytest.mark.run(order=0x01)
@pytest.mark.dependency(depends=['test_logModule'])
def test_getLogger():
    logger = log.getLogger('test')
    logger.setLevel(log.DEBUG)
    assert log.root.level == log.DEBUG
    assert logger.level == log.DEBUG
    assert logger.name == 'test'
    log.setLevel(log.INFO)
    assert log.root.level == log.INFO
    assert logger.level == log.INFO
    assert logger.name == 'test'
