import enum
import os
import re
import shutil
from typing import Optional

import attr

from aicompleter.handler import Handler
from aicompleter.interface.base import Interface
from aicompleter.session import Message, Session
from aicompleter.interface import User, Group
from aicompleter import error

class WorkSpace:
    '''
    WorkSpace for Autodone-AI
    To limit the scope of files
    '''
    def __init__(self, path:Optional[str] = None) -> None:
        self.path = path or os.path.abspath(os.getcwd())
        if self.path[-1] != os.sep:
            self.path += os.sep

    def __repr__(self) -> str:
        return f"WorkSpace({self.path})"
    
    def __str__(self) -> str:
        return self.path
    
    def check(self, path:str) -> bool:
        '''Check if the path is in the workspace.'''
        if path == self.path[:-1]:
            return True
        return os.path.abspath(path).startswith(self.path)
    
    def get_abspath(self, rela_path:str) -> str:
        '''Get absolute path from relative path'''
        if rela_path[0] == os.sep:
            return os.path.abspath(os.path.join(self.path,rela_path[1:]))
        return os.path.abspath(os.path.join(self.path,rela_path))

@enum.unique
class Type(enum.Enum):
    '''Type for file/folder'''
    File = enum.auto()
    Folder = enum.auto()
    Device = enum.auto()

@attr.s(auto_attribs=True, kw_only=True)
class SinglePermission:
    '''
    Single Permission for File
    '''
    readable = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    '''Readable'''
    writable = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    '''Writable'''
    executable = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    '''Executable. If folder, means can enter the folder'''

@attr.s(auto_attribs=True, kw_only=True)
class Permission:
    '''
    Permission for File
    '''
    owner:SinglePermission = attr.ib(default=SinglePermission(), validator=attr.validators.instance_of(SinglePermission))
    '''Owner Permission'''
    group:SinglePermission = attr.ib(default=SinglePermission(), validator=attr.validators.instance_of(SinglePermission))
    '''Group Permission'''
    other:SinglePermission = attr.ib(default=SinglePermission(), validator=attr.validators.instance_of(SinglePermission))
    '''Other Permission'''
    type:Type = attr.ib(default=Type.File, validator=attr.validators.instance_of(Type))
    '''Type of File'''

class File:
    '''
    File for Autodone-AI
    Use to check rights and read and write files
    '''
    default_permission = Permission(
        owner=SinglePermission(readable=True, writable=True, executable=False),
        group=SinglePermission(readable=True, writable=True, executable=False),
        other=SinglePermission(readable=True, writable=True, executable=False),
        type=Type.File
    )
    default_folder_permission = Permission(
        owner=SinglePermission(readable=True, writable=True, executable=True),
        group=SinglePermission(readable=True, writable=True, executable=True),
        other=SinglePermission(readable=True, writable=True, executable=True),
        type=Type.Folder
    )
    def __init__(self, handler:Handler, path:str) -> None:
        self.handler = handler
        self._path = os.path.abspath(path)
        '''Path of file'''
        self.owner:Optional[User] = None
        '''Owner of file'''
        self.owner_group:Optional[Group] = None
        '''Owner Group of file'''
        if not os.path.exists(path):
            raise error.NotFound('File Not Found', file=path)
        if not os.path.isfile(path):
            self.premission = File.default_folder_permission
            '''Permission of folder'''
        else:
            self.premission = File.default_permission
            '''Permission of file'''
        # TODO: device

    @property
    def path(self):
        '''Path of file'''
        return self._path

    def get_permission(self, user:User) -> SinglePermission:
        '''Get permission for user'''
        if self.owner == user:
            return self.premission.owner
        if self.owner_group in user.all_groups:
            return self.premission.group
        return self.premission.other

    def read(self, user:User, force:bool = False) -> str:
        '''
        Read file
        :param user: User
        :param force: Force to read
        '''
        if not force and not self.get_permission(user).readable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        with open(self.path, 'r') as f:
            return f.read()

    def write(self, user:User, content:str, force:bool = False) -> None:
        '''
        Write file
        :param user: User
        :param content: Content to write
        :param force: Force to write
        '''
        if not force and not self.get_permission(user).writable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        with open(self.path, 'w') as f:
            f.write(content)

    def execute(self, user:User, *args:object, force:bool = False, **kwargs:object):
        '''
        Execute file
        :param user: User
        :param args: args for asyncio.subprocess.create_subprocess_exec
        :param force: Force to execute
        :param kwargs: kwargs for asyncio.subprocess.create_subprocess_exec
        '''
        if not force and not self.get_permission(user).executable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        if self.premission.type == Type.Folder:
            raise error.PermissionDenied('Folder Not Executable', file=self.path)
        import asyncio.subprocess as subprocess
        return subprocess.create_subprocess_exec(self.path, *args, **kwargs)
    
    def listdir(self, user:User) -> list[str]:
        '''
        List dir
        :param user: User
        '''
        if self.premission.type == Type.File:
            raise error.PermissionDenied('File Not Listable', file=self.path)
        if not self.get_permission(user).executable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        return os.listdir(self.path)
    
    def mkdir(self, user:User, name:str, force:bool = False) -> None:
        '''
        Make dir
        :param user: User
        :param name: Name of dir
        :param force: Force to make dir
        '''
        if self.premission.type == Type.File:
            raise error.PermissionDenied('File Not Listable', file=self.path)
        if not self.get_permission(user).executable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        if not force and name in self.listdir(user):
            raise error.Existed('Already Exists', file=self.path)
        os.mkdir(os.path.join(self.path, name))

class FileSystem:
    '''
    File System for Autodone-AI
    Use to apply rights to files
    '''
    def __init__(self, handler:Handler, root:os.PathLike = os.getcwd()) -> None:
        self.handler = handler
        self._rights = {}
        self._files:set[File] = set()
        self._root:os.PathLike = os.path.abspath(root)
        if not os.path.exists(root):
            raise error.NotFound('File Not Found', file=root)
        if not os.path.isdir(root):
            raise error.NotFound('Not a Folder', file=root)
    
    @property
    def root(self):
        '''Root of FileSystem'''
        return self._root
    
    @root.setter
    def root(self, root:os.PathLike):
        '''
        Set root of FileSystem
        This will flush all files permission
        '''
        self._root = os.path.abspath(root)

    def _rm_file(self, path:os.PathLike):
        '''
        Remove File from cache
        :param path: Path of file
        '''
        for file in self._files:
            if file.path == path:
                self._files.remove(file)
                return

    def _get_by_abspath(self, path:os.PathLike) -> File:
        '''
        Get File by absolute path
        :param path: Absolute path
        :return: File
        '''
        if not os.path.exists(path):
            raise error.NotFound('File Not Found', file=path)
        for file in self._files:
            if file.path == path:
                return file
        file = File(self.handler, path)
        self._files.add(file)
        return file
    
    def _get_by_path(self, path:os.PathLike) -> File:
        '''
        Get File by path
        :param path: Path
        :return: File
        '''
        return self._get_by_abspath(os.path.join(self._root, path))
    
    def _check_list_dir_permission(self, user:User, path:os.PathLike) -> bool:
        '''
        Check if user can list the dir
        :param user: User
        :param path: Path(abs)
        '''
        if path == self._root:
            return
        parent = os.path.dirname(path)
        if parent != self._root:
            if not self._check_list_dir_permission(user, parent):
                return False
        else:
            # Root will be always True
            return True
        return self._get_by_abspath(path).get_permission(user).executable
        

    def get(self, path:os.PathLike, user:Optional[User] = None) -> File | None:
        '''
        Get File
        :param path: Path of file
        :return: File or None
        '''
        if path[0] != '/':
            raise error.InvalidPath('Invalid Path', path=path)
        path = os.path.join(self._root, path[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(path)):
                return None
        if not os.path.exists(path):
            return None
        return self._get_by_abspath(path)
    
    def remove(self, path:os.PathLike, user:Optional[User] = None):
        '''
        Remove File / Folder
        :param path: Path of file / folder
        :param user: User , if not None, will check permission
        '''
        if path[0] != '/':
            raise error.InvalidPath('Invalid Path', path=path)
        path = os.path.join(self._root, path[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(path)):
                raise error.PermissionDenied('Permission Denied', file=path)
        if not os.path.exists(path):
            raise error.NotFound('File Not Found', file=path)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        self._rm_file(path)

    def move(self, from_:os.PathLike, to_:os.PathLike, force:bool = False,user:Optional[User] = None):
        '''
        Move File
        :param from_: From
        :param to_: To
        :param force: Force to move (will overwrite)
        :param user: User , if not None, will check permission
        '''
        if from_[0] != '/':
            raise error.InvalidPath('Invalid Path', path=from_)
        if to_[0] != '/':
            raise error.InvalidPath('Invalid Path', path=to_)
        from_ = os.path.join(self._root, from_[1:])
        to_ = os.path.join(self._root, to_[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(from_)):
                raise error.PermissionDenied('Permission Denied', file=from_)
            if not self._check_list_dir_permission(user, os.path.dirname(to_)):
                raise error.PermissionDenied('Permission Denied', file=to_)
        if not os.path.exists(from_):
            raise error.NotFound('File Not Found', file=from_)
        if os.path.exists(to_) and not force:
            raise error.Existed('Already Exists', file=to_)
        os.rename(from_, to_)
        self._rm_file(from_)

    def copy(self, from_:os.PathLike, to_:os.PathLike, force:bool = False,user:Optional[User] = None):
        '''
        Copy File
        :param from_: From
        :param to_: To
        :param force: Force to copy (will overwrite)
        :param user: User , if not None, will check permission
        '''
        if from_[0] != '/':
            raise error.InvalidPath('Invalid Path', path=from_)
        if to_[0] != '/':
            raise error.InvalidPath('Invalid Path', path=to_)
        from_ = os.path.join(self._root, from_[1:])
        to_ = os.path.join(self._root, to_[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(from_)):
                raise error.PermissionDenied('Permission Denied', file=from_)
            if not self._check_list_dir_permission(user, os.path.dirname(to_)):
                raise error.PermissionDenied('Permission Denied', file=to_)
        if not os.path.exists(from_):
            raise error.NotFound('File Not Found', file=from_)
        if os.path.exists(to_) and not force:
            raise error.Existed('Already Exists', file=to_)
        shutil.copy(from_, to_)
        self._rm_file(to_)
