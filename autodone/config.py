'''
Name: config.py
Description: Configuration file for autodone
'''
from __future__ import annotations
import os
import json
from typing import Any
from utils import defaultdict

class Config(defaultdict):
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
    
    def save(self, path:str) -> None:
        with open(path, "w" ,encoding='utf-8') as f:
            json.dump(self, f, indent=4)

    @property
    def interfaces(self) -> Config:
        '''Get interfaces'''
        return self.get("interfaces")
    
    @property
    def handler(self) -> Config:
        '''Get handler'''
        return self.get("handler")

    @property
    def global_(self) -> Config:
        '''Get global config'''
        return self.get("global")

    def set(self, path:str, value:Any):
        spilts = path.split('.',2)
        if len(spilts) == 1:
            self[path] = value
        else:
            self[spilts[0]].set(spilts[1], value)

    def get(self, path:str, default:Any = None) -> Any:
        spilts = path.split('.',2)
        if len(spilts) == 1:
            return super().get(path, default)
        else:
            return self[spilts[0]].get(spilts[1], default)
        
    def __str__(self) -> str:
        return json.dumps(self, indent=4)
    
    def __repr__(self) -> str:
        return f"<Config {str(self)}>"
    
def loadConfig(path:str) -> Config:
    '''Load configuration from file'''
    return Config.loadFromFile(path)
