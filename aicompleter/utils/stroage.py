import contextlib
import json
import os
from typing import Literal, Optional, Self
import uuid
import attr
from ..common import JSONSerializable, JsonType, serialize

@attr.dataclass(frozen=True)
class Stroage:
    '''
    Stroage Metadata

    Args:
    ----------
    mark: JSONSerializable - file mark
    name: str - file name
    type: Literal['file', 'stroage', 'folder'] - file type
    '''
    mark:JSONSerializable | JsonType
    '''
    The stroage mark
    this identifies the stroage uniquely
    '''
    name:str = attr.ib(default=None)
    '''
    File name
    '''
    type:Literal['file', 'stroage', 'folder'] = 'file'
    '''
    File type
    '''

    def asdict(self):
        return {
            'mark': serialize(self.mark) if not isinstance(self.mark, JsonType) else self.mark,
            'name': self.name,
            'type': self.type,
            'mark-serialized': not isinstance(self.mark, JsonType)
        }
    
    @classmethod
    def fromdict(cls, data:dict):
        if data['mark-serialized']:
            data['mark'] = json.loads(data['mark'])
        del data['mark-serialized']
        return cls(**data)

class StroageManager:
    '''
    Stroage Metadata Manager

    Args:
    ----------
    basepath: str - base path

    '''
    def __init__(self, basepath:str):
        self._basepath = basepath
        with contextlib.suppress(FileNotFoundError):
            os.makedirs(basepath)
        if not os.path.isdir(basepath):
            raise ValueError(f'{basepath} is not a directory')
        self._metas:list[Stroage] = []
        self._indexfile = os.path.join(basepath, 'index.json')

    @classmethod
    def load(cls, basepath:str):
        '''
        Load Stroage Metadata Manager

        Args:
        ----------
        basepath: str - base path

        Returns:
        ----------
        StroageManager
        '''
        manager = cls(basepath)
        with open(manager._indexfile, 'r') as f:
            manager._metas = [Stroage.fromdict(meta) for meta in json.load(f)]
        return manager

    def save(self):
        '''
        Save Stroage Metadata Manager
        '''
        with open(self._indexfile, 'w') as f:
            json.dump([meta.asdict() for meta in self._metas], f)

    def __getitem__(self, mark:JSONSerializable|JsonType):
        for meta in self._metas:
            if meta.mark == mark:
                return meta
        raise KeyError(f'No stroage with mark {mark}')
    
    def __contains__(self, mark:JSONSerializable|JsonType):
        for meta in self._metas:
            if meta.mark == mark:
                return True
        return False
    
    def __iter__(self):
        return iter(self._metas)
    
    def __len__(self):
        return len(self._metas)
    
    def findmark(self, name:str):
        '''
        Find stroage mark by name

        Args:
        ----------
        name: str - stroage name

        Returns:
        ----------
        mark if found else None
        '''
        for meta in self._metas:
            if meta.name == name:
                return meta.mark
        return None

    def _get_available_name(self, subfix:str = ''):
        while True:
            name = str(uuid.uuid4()) + subfix
            if self.findmark(name) is None and not os.path.exists(os.path.join(self._basepath, name)):
                return name

    def alloc_file(self, mark:JSONSerializable|JsonType, recommended_subfix:Optional[str] = None):
        '''
        Allocate a file

        Args:
        ----------
        mark: JSONSerializable - file mark
        recommended_subfix: Optional[str] - recommended file subfix

        Returns:
        ----------
        The absoult path of the file
        '''
        if mark in self:
            raise KeyError(f'Stroage with mark {mark} already exists')
        meta = Stroage(mark, self._get_available_name(recommended_subfix or ''))
        self._metas.append(meta)
        return os.path.join(self._basepath, meta.name)

    def alloc_folder(self, mark:JSONSerializable|JsonType):
        '''
        Allocate a folder

        Args:
        ----------
        mark: JSONSerializable - folder mark

        Returns:
        ----------
        The absoult path of the folder (created)
        '''
        if mark in self:
            raise KeyError(f'Stroage with mark {mark} already exists')
        meta = Stroage(mark, self._get_available_name(), 'folder')
        self._metas.append(meta)
        os.mkdir(os.path.join(self._basepath, meta.name))
        return os.path.join(self._basepath, meta.name)
    
    def alloc_stroage(self, mark:JSONSerializable|JsonType) -> Self:
        '''
        Allocate a stroage

        Args:
        ----------
        name: str - stroage name
        mark: JSONSerializable - stroage mark

        Returns:
        ----------
        New StroageManager instance of the allocated folder
        '''
        if mark in self:
            raise KeyError(f'Stroage with mark {mark} already exists')
        meta = Stroage(mark, self._get_available_name(), 'stroage')
        self._metas.append(meta)
        return type(self)(os.path.join(self._basepath, meta.name))

    def delete(self, mark:JSONSerializable|JsonType):
        '''
        Delete stroage

        Args:
        ----------
        mark: JSONSerializable - stroage mark
        '''
        for meta in self._metas:
            if meta.mark == mark:
                self._metas.remove(meta)
                return
        raise KeyError(f'No stroage with mark {mark}')
