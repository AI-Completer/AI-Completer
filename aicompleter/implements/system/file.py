import os
import uuid
from typing import Optional
from aicompleter import *
from aicompleter.interface import User, Group
import aicompleter.session as session
from aicompleter.utils import Struct
from ...interface import CommandAuthority
from . import *

# File Interface
# TODO: add more file operations
class FileInterface(Interface):
    '''
    File Interface for Autodone-AI

    Including File Read and Write
    '''
    def __init__(self, config:Config = Config(), id: Optional[uuid.UUID] = uuid.uuid4()):
        super().__init__(
            namespace="file",
            user = User(
                name="file",
                in_group="system",
                all_groups={"system","command"},
                support={"text","file"}
            ),
            id=id,
            config = config,
        )
        self.commands.add(
            Command(
                cmd='read',
                description='Read a file',
                callback=self.cmd_read,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='File Path',tooltip='filepath')
                }),
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_readfile=True,
                )
            ),
            Command(
                cmd='write',
                description='Write a file',
                callback=self.cmd_write,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='File Path',tooltip='filepath'),
                    'content': CommandParamElement('content', str, description='File Content'),
                    'append': CommandParamElement('append', bool, description='Append',tooltip='append-mode', optional=True, default=False),
                }),
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_writefile=True,
                )
            ),
            Command(
                cmd='listdir',
                description='List the contents of a directory',
                callback=self.cmd_listdir,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='Directory Path',tooltip='path', default='.', optional=True)
                }),
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_listfile=True,
                )
            ),
        )

    async def session_init(self, session:Session):
        # This data will be reuseable in other interfaces
        data = self.getdata(session)
        data['filesystem'] = FileSystem(session.config[self.namespace.name].get('root', 'workspace'))
        data['workspace'] = WorkSpace(data['filesystem'], '/')

    def getworkspace(self, session:Session) -> WorkSpace:
        return self.getdata(session)['workspace']

    async def cmd_read(self, session:Session, message:Message) -> str:
        '''Command for reading file'''
        data = self.getdata(session)
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = data['filesystem']
        workspace:WorkSpace = data['workspace']
        file = workspace.get(path, message.src_interface.user if message.src_interface else None)
        if not file:
            raise FileNotFoundError(f'File {path} not found or no permission')
        if not file.type == Type.File:
            raise FileNotFoundError(f'File {path} is not a file')
        return file.read(message.src_interface.user if message.src_interface else None)
    
    async def cmd_write(self, session:Session, message:Message) -> str:
        '''Command for writing file'''
        data = self.getdata(session)
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = data['filesystem']
        workspace:WorkSpace = data['workspace']
        file = workspace.get(path, message.src_interface.user if message.src_interface else None)
        if not file:
            raise FileNotFoundError(f'File {path} no permission')
        if not file.existed:
            return file.write(message.content.json['content'], message.src_interface.user if message.src_interface else None)
        if not file.type == Type.File:
            raise FileNotFoundError(f'File {path} is not a file')
        if message.content.json['append']:
            return file.write_append(message.content.json['content'], message.src_interface.user if message.src_interface else None)
        return file.write(message.content.json['content'], message.src_interface.user if message.src_interface else None)

    async def cmd_listdir(self, session:Session, message:Message) -> list[str]:
        '''Command for listing directory'''
        data = self.getdata(session)
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = data['filesystem']
        workspace:WorkSpace = data['workspace']
        file = workspace.get(path, message.src_interface.user if message.src_interface else None)
        if not file:
            raise FileNotFoundError(f'Path {path} not found or no permission')
        if not file.type == Type.Folder:
            raise FileNotFoundError(f'Path {path} is not a directory')
        return file.listdir(message.src_interface.user if message.src_interface else None)
