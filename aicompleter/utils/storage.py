from __future__ import annotations
import contextlib
import json
import os
from typing import Literal, Optional, Self
import uuid
import attr
from ..common import JSONSerializable, JsonType, serialize

@attr.dataclass(frozen=True)
class Storage:
    '''
    Storage Metadata

    Args:
    ----------
    mark: JSONSerializable - file mark
    name: str - file name
    type: Literal['file', 'storage', 'folder'] - file type
    '''
    mark:JSONSerializable | JsonType
    '''
    The storage mark
    this identifies the storage uniquely
    '''
    name:str = attr.ib(default=None)
    '''
    File name
    '''
    type:Literal['file', 'storage', 'folder'] = 'file'
    '''
    File type
    '''

    in_manager:Optional[StorageManager] = attr.ib(default=None, repr=False)
    @property
    def path(self):
        '''
        Get the file path
        '''
        return os.path.join(self.in_manager._basepath, self.name)

    def asdict(self):
        return {
            'mark': serialize(self.mark) if not isinstance(self.mark, JsonType) else self.mark,
            'name': self.name,
            'type': self.type,
            'mark-serialized': not isinstance(self.mark, JsonType)
        }
    
    @classmethod
    def fromdict(cls, data:dict, in_manager:Optional[StorageManager]=None):
        if data['mark-serialized']:
            data['mark'] = json.loads(data['mark'])
        del data['mark-serialized']
        if in_manager != None:
            data['in_manager'] = in_manager
        return cls(**data)

class StorageManager:
    '''
    Storage Metadata Manager

    Args:
    ----------
    basepath: str - base path

    '''
    def __init__(self, basepath:str):
        self._basepath = basepath
        with contextlib.suppress(FileExistsError):
            os.mkdir(basepath)
        if not os.path.isdir(basepath):
            raise ValueError(f'{basepath} is not a directory')
        self._metas:list[Storage] = []
        self._indexfile = os.path.join(basepath, 'index.json')

    @property
    def path(self):
        '''
        Get the base path
        '''
        return self._basepath

    @classmethod
    def load(cls, basepath:str):
        '''
        Load Storage Metadata Manager

        Args:
        ----------
        basepath: str - base path

        Returns:
        ----------
        StorageManager
        '''
        manager = cls.__new__(cls)
        manager._basepath = basepath
        manager._indexfile = os.path.join(basepath, 'index.json')
        with open(manager._indexfile, 'r') as f:
            manager._metas = [Storage.fromdict(meta, manager) for meta in json.load(f)]
        return manager

    def save(self):
        '''
        Save Storage Metadata Manager
        '''
        with open(self._indexfile, 'w') as f:
            json.dump([meta.asdict() for meta in self._metas], f)

    @staticmethod
    def isstoragedir(path:str):
        '''
        Test whether a folder is a storage folder
        '''
        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, 'index.json')):
                return True
        return False

    def __getitem__(self, mark:JSONSerializable|JsonType):
        for meta in self._metas:
            if meta.mark == mark:
                return meta
        raise KeyError(f'No storage with mark {mark}')
    
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
        Find storage mark by name

        Args:
        ----------
        name: str - storage name

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
            raise KeyError(f'Storage with mark {mark} already exists')
        meta = Storage(mark, self._get_available_name(recommended_subfix or ''), in_manager=self)
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
            raise KeyError(f'Storage with mark {mark} already exists')
        meta = Storage(mark, self._get_available_name(), 'folder', in_manager=self)
        self._metas.append(meta)
        os.mkdir(os.path.join(self._basepath, meta.name))
        return os.path.join(self._basepath, meta.name)
    
    def alloc_storage(self, mark:JSONSerializable|JsonType) -> Self:
        '''
        Allocate a storage

        Args:
        ----------
        name: str - storage name
        mark: JSONSerializable - storage mark

        Returns:
        ----------
        New StorageManager instance of the allocated folder
        '''
        if mark in self:
            raise KeyError(f'Storage with mark {mark} already exists')
        meta = Storage(mark, self._get_available_name(), 'storage', in_manager=self)
        self._metas.append(meta)
        return type(self)(os.path.join(self._basepath, meta.name))

    def delete(self, mark:JSONSerializable|JsonType):
        '''
        Delete storage

        Args:
        ----------
        mark: JSONSerializable - storage mark
        '''
        for meta in self._metas:
            if meta.mark == mark:
                self._metas.remove(meta)
                return
        raise KeyError(f'No storage with mark {mark}')
