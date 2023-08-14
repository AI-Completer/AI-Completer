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
    # Normal dict
    assert isinstance(config['a'], str)
    assert isinstance(config['c']['d'], str)
    assert isinstance(config['c']['f'], list)

    # Wrapped dict
    assert isinstance(config['c'], ac.Config)
    
    # JSON structure
    assert isinstance(config['c.d'], str)

    # Test value
    assert config['a'] == 'b'
    assert config['c.d'] == 'e'

    config['a'] = 'm'
    assert config['a'] == 'm'

    config['c.d'] = 'n'
    assert config['c.d'] == 'n'

    config['c.f'] = {'a': 'b'}
    assert isinstance(config['c.f'], ac.Config)
    assert config['c.f.a'] == 'b'
    
    # Disable disallowed type
    with pytest.raises(TypeError):
        config['a'] = lambda: None

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


