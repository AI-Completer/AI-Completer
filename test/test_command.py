import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import aicompleter as ac

@pytest.mark.run(order=0x20)
@pytest.mark.dependency()
def test_Format():
    struct = ac.CommandParamStruct({
        'key': ac.CommandParam('key', type=int),
        'key2': ac.CommandParam('key2', type=str, default='default', optional=True),
    })
    assert struct.check({'key': 1})
    assert not struct.check({'key': '1'})
    assert not struct.check({'wrong-key': 1})
    assert not struct.check({'key': 1, 'key2': 2})
    assert struct.check({'key': 1, 'key2': '2'})

@pytest.mark.run(order=0x21)
@pytest.mark.dependency(depends=['test_Format'])
def test_BaseCommand():
    ac.Command('cmd')
    cmd = ac.Command('cmd', 'desc')
    assert cmd.name == 'cmd'
    cmd = ac.Command('cmd', 'desc',
        format=ac.CommandParamStruct({
            'key': ac.CommandParam('key', type=int),
            'key2': ac.CommandParam('key2', type=str, default='default', optional=True),
        })
    )
    testfunc = lambda key, key2: (key, key2)
    cmd.bind(testfunc)
    assert cmd.callback == testfunc
    assert cmd.check({'key': 1})
    assert not cmd.check({'key': '1'})
