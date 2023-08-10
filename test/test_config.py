import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aicompleter as ac
import pytest

def test_Config():
    config = ac.Config()
    config = ac.Config({
        'a': 'b',
        'c': {
            'd': 'e',
            'f': ['g', 'h']
        }
    })
    assert isinstance(config['a'], str)
    assert isinstance(config['c'], ac.Config)
    assert isinstance(config['c']['d'], str)
    assert isinstance(config['c']['f'], list)
    
    with pytest.raises(ac.error.ConfigureMissing):
        config.require('d')

    with pytest.raises(TypeError):
        config = ac.Config(1)


def test_ConfigModel():
    class TestModel(ac.ConfigModel):
        a: str
        b: int
        c: list
        d: dict

    class TestModel2(ac.ConfigModel, init=True):
        a: str
        b: int
        c: list
        d: dict

    assert TestModel(a='a', b=1, c=[1, 2, 3], d={'a': 'b'}) == TestModel(a='a', b=1, c=[1, 2, 3], d={'a': 'b'})
    assert TestModel(a='a', b=1, c=[1, 2, 3], d={'a': 'b'}) != TestModel(a='a', b=1, c=[1, 2, 3], d={'a': 'c'})

    # No default value
    TestModel()
    with pytest.raises(TypeError):
        TestModel2()

    class ParentModel(ac.ConfigModel):
        v: TestModel

    config = ParentModel({
        'v': {
            'a': 'a',
            'b': 1,
            'c': [1, 2, 3],
            'd': {'a': 'b'}
        }
    })

    assert isinstance(config.v, TestModel)
    assert config.v == TestModel(a='a', b=1, c=[1, 2, 3], d={'a': 'b'})


