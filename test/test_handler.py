import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aicompleter as ac
import pytest

# Require the config test to be passed
@pytest.mark.dependency(name="test_config", depends=["test_Config"])
def test_Handler():
    handler = ac.Handler()
    handler = ac.Handler(config=ac.Config({
        'global': {},
        'namespace1': {
            'a': 'b',
        },
    }))

    # TODO: Test the handler
