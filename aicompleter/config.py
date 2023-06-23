'''
Name: config.py
Description: Configuration file for aicompleter
'''
from __future__ import annotations

import json
import os
from re import A
from typing import Any

from .error import ConfigureMissing

from .utils import EnhancedDict

Pointer = list
'''
Pointer type
Use list to implement pointer
'''

class Config(EnhancedDict):
    '''Configuration Class'''
    ALLOWED_VALUE_TYPE = (str, int, float, bool, type(None))

    @staticmethod
    def loadFromFile(path:str) -> Config:
        '''
        Load Configuration From File
        The file should be in json format
        '''
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return Config(json.load(f))
        
    def require(self, path: str) -> Any:
        '''
        Require a value, raise ConfigureMissing if not found
        '''
        try:
            return super().require(path)
        except KeyError as e:
            raise ConfigureMissing(f"Configure missing: {path}",origin=self, parent=e) from e
        
    def save(self, path:str) -> None:
        '''
        Save the configuration to file
        '''
        with open(path, "w" ,encoding='utf-8') as f:
            json.dump(self, f, indent=4)

    @property
    def global_(self) -> Config:
        '''Get global config'''
        return self.get('global', Config())
    
    def __setitem__(self, __key: Any, __value: Any) -> None:
        # Check type
        def _check(key: Any, value: Any) -> None:
            if not isinstance(key, str):
                raise TypeError(f"Invalid key type: {key!r}")
            if isinstance(value, dict):
                for k, v in value.items():
                    _check(k, v)
                return
            if not isinstance(value, self.ALLOWED_VALUE_TYPE):
                raise TypeError(f"Invalid value type: {value!r}")
        _check(__key, __value)
        return super().__setitem__(__key, __value)
    
def loadConfig(path:str) -> Config:
    '''Load configuration from file'''
    return Config.loadFromFile(path)

__all__ = (
    'Pointer',
    'Config',
    'loadConfig',
)
