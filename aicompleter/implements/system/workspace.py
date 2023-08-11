'''
Virtual File System

This is a virtual file system prepared specially for AI Interface
'''

from __future__ import annotations
import enum
import os
import re
import shutil
from typing import Optional

import attr

from aicompleter.interface import User, Group
from aicompleter import error

sep = '/'

def normpath(path:str):
    '''Normalize path'''
    return os.path.normpath(path).replace('\\', '/')

def issamepath(path1:str, path2:str):
    '''Check if two path is the same'''
    return normpath(path1) == normpath(path2)

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
    readable:bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    '''Readable'''
    writable:bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    '''Writable'''
    executable:bool = attr.ib(default=False, validator=attr.validators.instance_of(bool))
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
    def __init__(self, path:str, in_filesystem: Optional[FileSystem] = None) -> None:
        self._in_filesystem = in_filesystem
        '''FileSystem of file'''
        self._path = normpath(path)
        '''Path of file'''
        self.owner:Optional[User] = None
        '''Owner of file'''
        self.owner_group:Optional[Group] = None
        '''Owner Group of file'''

        if not os.path.isabs(self._path):
            raise error.InvalidPath('Require Absoulte Path', path=self._path)
        
        if self.existed:
            if os.path.isfile(self._true_path):
                self.permission = File.default_permission
                '''Permission of file'''
            elif os.path.isdir(self._true_path):
                self.permission = File.default_folder_permission
                '''Permission of folder'''
            else:
                raise NotImplementedError('Unimplemented File Type')
        else:
            self.permission = File.default_permission

    @property
    def _true_path(self):
        '''
        Get true path (to the operating system)
        '''
        if self._in_filesystem is not None:
            if self._path == sep:
                return self._in_filesystem.root
            return os.path.join(str(self._in_filesystem.root).replace('\\','/'), self._path[1:]).replace(sep,os.sep)
        return self._path

    @property
    def existed(self):
        '''
        If file existed
        '''
        return os.path.exists(self._true_path)

    @property
    def path(self):
        '''
        Path of file
        If the file is in a FileSystem, the path will be relative to the root of FileSystem
        '''
        return self._path
    
    @property
    def isdir(self):
        '''
        If file is a dir
        '''
        return self.permission.type == Type.Folder
    
    @property
    def isfile(self):
        '''
        If file is a file
        '''
        return self.permission.type == Type.File
    
    @property
    def type(self):
        '''
        Type of file
        '''
        return self.permission.type
    
    def _check_file_exists(self):
        '''
        Check if file exists
        '''
        if not self.existed:
            raise error.NotFound('File Not Found', file=self.path)

    def get_permission(self, user:User) -> SinglePermission:
        '''
        Get permission for user
        :param user: User
        :return: Permission
        '''
        self._check_file_exists()
        if self.owner == user:
            return self.permission.owner
        if self.owner_group in user.all_groups:
            return self.permission.group
        return self.permission.other

    def read(self, user:Optional[User] = None) -> str:
        '''
        Read file
        :param user: User
        '''
        self._check_file_exists()
        force = user == None
        if not force and not self.get_permission(user).readable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        with open(self._true_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write(self, content:str, user:Optional[User] = None) -> None:
        '''
        Write file
        :param content: Content to write
        :param user: User
        '''
        force = user == None
        if not force and self.existed and not self.get_permission(user).writable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        with open(self._true_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def write_append(self, content:str, user:Optional[User] = None) -> None:
        '''
        Write file (append)
        :param content: Content to write
        :param user: User
        '''
        force = user == None
        if not force and not self.get_permission(user).writable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        with open(self._true_path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')

    def execute(self, user:Optional[User] = None, *args:object, **kwargs:object):
        '''
        Execute file
        :param user: User
        :param args: args for asyncio.subprocess.create_subprocess_exec
        :param force: Force to execute
        :param kwargs: kwargs for asyncio.subprocess.create_subprocess_exec
        '''
        self._check_file_exists()
        force = user == None
        if not force and not self.get_permission(user).executable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        if self.permission.type == Type.Folder:
            raise error.PermissionDenied('Folder Not Executable', file=self.path)
        import asyncio.subprocess as subprocess
        return subprocess.create_subprocess_exec(self.path, *args, **kwargs)
    
    def listdir(self, user: Optional[User] = None) -> list[str]:
        '''
        List dir
        :param user: Optional[User] if not None, will check permission
        '''
        self._check_file_exists()
        if self.permission.type == Type.File:
            raise error.PermissionDenied('File Not Listable', file=self.path)
        if user:
            if not self.get_permission(user).executable:
                raise error.PermissionDenied('Permission Denied', file=self.path)
        return os.listdir(self._true_path)
    
    def mkdir(self, name:str, user:Optional[User] = None) -> File:
        '''
        Make dir
        :param name: Name of dir
        :param user: Optional[User] if not None, will check permission
        '''
        self._check_file_exists()
        # Check The name
        force = user == None
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
            raise error.InvalidPath('Invalid Name', name=name)
        if self.permission.type == Type.File:
            raise error.PermissionDenied('File Not Listable', file=self.path)
        if not self.get_permission(user).executable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        if not force and name in self.listdir(user):
            raise error.Existed('Already Exists', file=self.path)
        os.mkdir(os.path.join(self._true_path, name))
        return File(os.path.join(self._true_path, name), self._in_filesystem)
    
    def open(self, mode:str, user:Optional[User] = None, *args, **kwargs):
        '''
        Open file
        :param mode: Mode
        :param user: Optional[User] if not None, will check permission
        :param args: args for open
        :param kwargs: kwargs for open
        '''
        if not self.existed:
            if 'w' not in mode and 'a' not in mode and '+' not in mode:
                raise error.NotFound('File Not Found', file=self.path)
            pre = self.default_permission.owner
        else:
            pre = self.get_permission(user)
        if 'r' in mode and not pre.readable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        if ('w' in mode or '+' in mode) and not pre.writable:
            raise error.PermissionDenied('Permission Denied', file=self.path)
        return open(self._true_path, mode, *args, **kwargs)

class FileSystem:
    '''
    File System for Autodone-AI
    Use to apply rights to files
    '''
    def __init__(self, root:os.PathLike = os.getcwd()) -> None:
        self._files:set[File] = set()
        self._root:os.PathLike = os.path.abspath(root)
        if not os.path.exists(root):
            raise error.NotFound('File Not Found', file=root)
        if not os.path.isdir(root):
            raise error.NotFound('Not a Folder', file=root)
        if not self._root[-1] == os.sep:
            self._root += os.sep
            # Add a slash to the end of root
    
    @property
    def root(self):
        '''
        Root of FileSystem (to the operating system)
        :return: Root of FileSystem
        '''
        return self._root
    
    @root.setter
    def root(self, root:os.PathLike):
        '''
        Set root of FileSystem
        This will flush all files permission
        :param root: Root of FileSystem
        '''
        self._root = os.path.abspath(root)
        # Clear all cached files
        self._files.clear()

    def _rm_file(self, path:os.PathLike):
        '''
        Remove File from cache
        :param path: Path of file
        '''
        path = normpath(path)
        for file in self._files:
            if file.path == path:
                self._files.remove(file)
                return

    def _get_by_abspath(self, path:os.PathLike) -> File:
        '''
        Get File by absolute path (to the operating system)
        :param path: Absolute path
        :return: File
        '''
        path = os.path.normpath(path)
        # This will not check if the file exists
        for file in self._files:
            if issamepath(file._true_path,path):
                return file
        file = File('/' + str(path[len(self.root):]).replace('\\','/'), self)
        self._files.add(file)
        return file
    
    def _get_by_path(self, path:os.PathLike) -> File:
        '''
        Get File by path (to the FileSystem object)
        :param path: Path
        :return: File
        '''
        return self._get_by_abspath(os.path.join(self._root, path))
    
    def _check_list_dir_permission(self, user:User, path:os.PathLike) -> bool:
        '''
        Check if user can list the dir (Note: the directory can be not existed)
        :param user: User
        :param path: Path(abs)
        '''
        path = normpath(path)
        if issamepath(path, self._root):
            return True
        parent = os.path.dirname(path)
        if parent != self._root:
            if not self._check_list_dir_permission(user, parent):
                return False
        else:
            # Root will be always True
            return True
        return self._get_by_abspath(path).get_permission(user).executable

    def get(self, path:os.PathLike, user:Optional[User] = None) -> File:
        '''
        Get File
        :param path: Path of file
        :param user: User , if not None, will check permission
        :return: File
        '''
        path = normpath(path)
        if path[0] != sep:
            raise error.InvalidPath('Invalid Path', path=path)
        path = os.path.join(self._root, path[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(path)):
                raise error.PermissionDenied('Permission Denied', file=path)
        # if not os.path.exists(path):
        #     raise error.NotFound('File Not Found', file=path)
        return self._get_by_abspath(path)
    
    def remove(self, path:os.PathLike, user:Optional[User] = None):
        '''
        Remove File / Folder
        :param path: Path of file / folder
        :param user: User , if not None, will check permission
        '''
        path = normpath(path)
        if path[0] != sep:
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

    def move(self, from_:os.PathLike, to_:os.PathLike, force:bool = True, user:Optional[User] = None):
        '''
        Move File
        :param from_: From
        :param to_: To
        :param force: Force to move (will overwrite)
        :param user: User , if not None, will check permission
        '''
        from_ = normpath(from_)
        to_ = normpath(to_)
        if from_[0] != sep:
            raise error.InvalidPath('Invalid Path', path=from_)
        if to_[0] != sep:
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
        from_ = normpath(from_)
        to_ = normpath(to_)
        if from_[0] != sep:
            raise error.InvalidPath('Invalid Path', path=from_)
        if to_[0] != sep:
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

    def mkdir(self, path:os.PathLike, user:Optional[User] = None):
        '''
        Make dir
        :param path: Path of dir
        :param user: User , if not None, will check permission
        '''
        path = normpath(path)
        if path[0] != sep:
            raise error.InvalidPath('Invalid Path', path=path)
        path = os.path.join(self._root, path[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(path)):
                raise error.PermissionDenied('Permission Denied', file=path)
            # Check write permission
            if not self._get_by_abspath(os.path.dirname(path)).get_permission(user).writable:
                raise error.PermissionDenied('Permission Denied', file=path)
        if os.path.exists(path):
            raise error.Existed('Already Exists', file=path)
        os.mkdir(path)
        self._rm_file(path)

    def new(self, path:str, user:Optional[User] = None):
        '''
        New File
        :param path: Path of file
        :param user: User , if not None, will check permission
        '''
        path = normpath(path)
        if path[0] != sep:
            raise error.InvalidPath('Invalid Path', path=path)
        path = os.path.join(self._root, path[1:])
        if user is not None:
            # Check if user can list the parent folder
            if not self._check_list_dir_permission(user, os.path.dirname(path)):
                raise error.PermissionDenied('Permission Denied', file=path)
            # Check write permission
            if not self._get_by_abspath(os.path.dirname(path)).get_permission(user).writable:
                raise error.PermissionDenied('Permission Denied', file=path)
        if os.path.exists(path):
            raise error.Existed('Already Exists', file=path)
        with open(path, 'w', encoding='utf-8') as f:
            pass
        # Create File Object
        return self._get_by_abspath(path)

class WorkSpace:
    '''
    WorkSpace for AI-Completer
    To limit the scope of files

    :param filesystem: FileSystem
    :param init_path: Init Path (Absolute Path to the file system)
    '''
    def __init__(self, filesystem: FileSystem, init_path: os.PathLike) -> None:
        self._fs = filesystem
        self._file = filesystem.get(init_path)
        if self._file is None:
            raise error.NotFound('Folder Not Found', file=init_path)
        if self._file.permission.type != Type.Folder:
            raise error.PermissionDenied('Not a Folder', file=init_path)

    def new(self, path:os.PathLike, user:Optional[User] = None) -> File:
        '''
        New File
        :param path: Path of file (enable relative path to outside of workspace)
        :param user: User , if not None, will check permission
        '''
        if path[0] != sep:
            # Relative path
            return self._fs.new(os.path.join(self._file.path, path), user)
        return self._fs.new(path, user)
    
    def remove(self, path:os.PathLike, user:Optional[User] = None):
        '''
        Remove File / Folder
        :param path: Path of file / folder (enable relative path to outside of workspace)
        :param user: User , if not None, will check permission
        '''
        if path[0] != sep:
            # Relative path
            return self._fs.remove(os.path.join(self._file.path, path), user)
        return self._fs.remove(path, user)
    
    def get(self, path:os.PathLike, user:Optional[User] = None) -> File | None:
        '''
        Get File
        :param path: Path of file (enable relative path to outside of workspace)
        :param user: User , if not None, will check permission
        :return: The file of specified path, None if not exists
        '''
        if path[0] != sep:
            # Relative path
            return self._fs.get(os.path.join(self._file.path, path), user)
        return self._fs.get(path, user)
    
    def mkdir(self, path:os.PathLike, user:Optional[User] = None):
        '''
        Make dir
        :param path: Path of dir (enable relative path to outside of workspace)
        :param user: User , if not None, will check permission
        '''
        if path[0] != sep:
            # Relative path
            return self._fs.mkdir(os.path.join(self._file.path, path), user)
        return self._fs.mkdir(path, user)
    
    def check_in(self, path:os.PathLike) -> bool:
        '''
        Check if the file is in the workspace (no matter the file is existed or not)
        :param path: Path of file
        :return: True if in workspace
        '''
        if path[0] != sep:
            # Relative path
            return str(normpath(os.path.join(self._file.path, path))).startswith(self._file.path)
        path = normpath(path)
        return str(path).startswith(self._file.path)
