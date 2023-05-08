'''
Name: config.py
Description: Configuration file for autodone
'''
from __future__ import annotations
import os
import json
from tkinter import E
from typing import Any, Self, TypeVar
from autodone.error import ConfigureMissing
from utils import defaultdict
import copy

Pointer = TypeVar('Pointer', list)
'''
Pointer type
Use list to implement pointer
'''

class EnhancedDict(defaultdict):
    '''
    Enhanced dict
    '''
    def __init__(self, readonly:bool = True,*args, **kwargs) -> None:
        self._readonly = readonly
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    @property
    def readonly(self) -> bool:
        '''Get readonly'''
        return self._readonly
    
    @readonly.setter
    def readonly(self, value:bool) -> None:
        '''Set readonly'''
        self._readonly = value

    def set(self, path:str, value:Any):
        '''
        Set a value
        '''
        if not self._writeable:
            raise AttributeError("EnhancedDict is not writeable")
        if '.' in path:
            spilts = path.split('.',2)
            if spilts[0] not in self:
                super().__setitem__(spilts[0], self.__class__())
            self[spilts[0]][spilts[1]] = value
            return
        if isinstance(value, dict):
            value = self.__class__(value)
        return super().__setitem__(path, value)

    def get(self, path:str, default:Any = None) -> Any:
        '''
        Get a value
        '''
        spilts = path.split('.',2)
        if len(spilts) == 1:
            ret = super().get(path, default)
            if isinstance(ret, dict):
                return self.__class__(ret)
        else:
            return self[spilts[0]].get(spilts[1], default)
        
    def has(self, path:str) -> bool:
        '''
        Check whether the path exists
        '''
        spilts = path.split('.',2)
        if len(spilts) == 1:
            return path in self
        else:
            return self[spilts[0]].has(spilts[1])
        
    def require(self, path:str) -> Any:
        '''
        Require a value, raise KeyError if not found
        '''
        if not self.has(path):
            raise KeyError(f"Key not found: {path}")
        return self.get(path)
        
    def setdefault(self, path:str, default:Any = None) -> Any:
        if self._readonly:
            raise AttributeError("Config is not writeable")
        spilts = path.split('.',2)
        if len(spilts) == 1:
            return super().setdefault(path, default)
        else:
            return self[spilts[0]].setdefault(spilts[1], default)
        
    def __str__(self) -> str:
        return json.dumps(self, indent=4)
    
    def __repr__(self) -> str:
        return f"<Config {str(self)}>"
    
    def __delitem__(self, __key: Any) -> None:
        if not self._writeable:
            raise AttributeError("Config is not writeable")
        return super().__delitem__(__key)
    
    def __contains__(self, __key: object) -> bool:
        spilts = __key.split('.',2)
        if len(spilts) == 1:
            return super().__contains__(__key)
        else:
            return self[spilts[0]].__contains__(spilts[1])
    
    __getitem__ = get
    __setitem__ = set
    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__

    class __Session:
        '''
        Open a session to modify the EnhancedDict
        '''
        def __init__(self, dict:EnhancedDict, locked:bool, save:bool) -> None:
            self.locked = locked
            if save:
                self._dict = dict
            else:
                self._dict = copy.deepcopy(dict)
        
        def __enter__(self) -> EnhancedDict:
            if self.locked:self._dict._readonly = False
            return self._dict
        
        def __exit__(self, exc_type, exc_value, traceback) -> None:
            if self.locked:self._dict._readonly = True

    def session(self, locked:bool = True, save:bool = True) -> __Session:
        '''
        Open a session to modify the EnhancedDict
        param:
            locked: Whether the session is locked
            save: Whether to save the dict after the session
        '''
        return self.__Session(self, locked, save)

class Config(EnhancedDict):
    '''Configuration Class'''
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
        try:
            return super().require(path)
        except KeyError as e:
            raise ConfigureMissing(f"Configure missing: {path}",parent=e) from e
        
    def save(self, path:str) -> None:
        with open(path, "w" ,encoding='utf-8') as f:
            json.dump(self, f, indent=4)
    
def loadConfig(path:str) -> Config:
    '''Load configuration from file'''
    return Config.loadFromFile(path)


