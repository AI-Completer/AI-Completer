'''
Name: config.py
Description: Configuration file for autodone
'''
from __future__ import annotations
from asyncio import Lock
import asyncio
import os
import json
from typing import Any, Callable, Optional, Self, TypeVar
from autodone.error import ConfigureMissing
from .utils import defaultdict
import copy

Pointer = list
'''
Pointer type
Use list to implement pointer
'''

class EnhancedDict(defaultdict):
    '''
    Enhanced dict
    param:
        readonly: bool, Optional, default: False, readonly or not
    '''
    def __update_dict(self) -> None:
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = self.__class__(value, readonly=self._lock.locked())
    
    def __init__(self, *args, **kwargs) -> None:
        self._lock:Lock = asyncio.Lock()
        self._lock._locked = kwargs.pop('readonly', False)
        if not isinstance(self._lock._locked, bool):
            raise TypeError("readonly must be bool")
        super().__init__(*args, **kwargs)
        self.__update_dict()

    def __missing__(self, key):
        self[key] = self.__class__()
        return super().__getitem__(key)

    @property
    def readonly(self) -> bool:
        '''
        Get readonly
        This identifies whether the dict is occupied by a session
        '''
        return self._lock.locked()

    def set(self, path:str, value:Any):
        '''
        Set a value
        '''
        if '.' in path:
            spilts = path.split('.', 1)
            if spilts[0] not in self:
                super().__setitem__(spilts[0], self.__class__())
            super().__getitem__(spilts[0]).set(spilts[1],value)
            return
        if isinstance(value, dict):
            value = self.__class__(value)
        return super().__setitem__(path, value)

    def get(self, path:str, default:Any = None) -> Any:
        '''
        Get a value
        '''
        spilts = path.split('.', 1)
        if len(spilts) == 1:
            if default is None:
                if path not in self:
                    return self.__class__()
            ret = super().get(path, default)
            if isinstance(ret, dict):
                return self.__class__(ret)
            return ret
        else:
            return self[spilts[0]].get(spilts[1], default)
        
    def has(self, path:str) -> bool:
        '''
        Check whether the path exists
        '''
        spilts = path.split('.', 1)
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
        '''
        Set a value if not exists
        param:
            path: The path of the value
            default: The default value
        '''
        spilts = path.split('.', 1)
        if len(spilts) == 1:
            return super().setdefault(path, default)
        else:
            return self[spilts[0]].setdefault(spilts[1], default)
        
    def update(self, data:EnhancedDict):
        '''Update the dict'''
        for key, value in data.items():
            if isinstance(value, EnhancedDict):
                if key not in self:
                    self[key] = data.__class__()
                self[key].update(value)
            else:
                self[key] = value
        
    def __str__(self) -> str:
        return json.dumps(self, indent=4)
    
    def __repr__(self) -> str:
        return f"<Config {str(self)}>"
    
    def __delitem__(self, __key: Any) -> None:
        return super().__delitem__(__key)
    
    def __contains__(self, __key: str) -> bool:
        spilts = __key.split('.', 1)
        if len(spilts) == 1:
            return super().__contains__(__key)
        else:
            return self[spilts[0]].__contains__(spilts[1])
    
    def __getitem__(self, __key: str) -> Any:
        spilts = __key.split('.', 1)
        if len(spilts) == 1:
            return super().__getitem__(__key)
        else:
            return self[spilts[0]].__getitem__(spilts[1])

    __setitem__ = set

    def __bool__(self) -> bool:
        return self.__len__() != 0

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
        
        async def __aenter__(self) -> EnhancedDict:
            await self._dict._lock.acquire()
            return self._dict
        
        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            self._dict._lock.release()

    def session(self, locked:bool = True, save:bool = True) -> __Session:
        '''
        Open a session to modify the EnhancedDict
        param:
            locked: Whether the session is locked, this will occupy the dict, if the save is False
            save: Whether to save the dict after the session
        '''
        return self.__Session(self, locked, save)
    
    def each(self, func:Callable[[str, Any], Any], filter:Optional[Callable[[str, Any], bool]] = None) -> None:
        '''
        Call the function for each value
        
        :param func: The function to call
        :param filter: The filter function
        '''
        for key, value in self.items():
            if filter is None or filter(key, value):
                func(key, value)

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
    
def loadConfig(path:str) -> Config:
    '''Load configuration from file'''
    return Config.loadFromFile(path)


