import os
import uuid
from typing import Optional
from aicompleter import *
from aicompleter.interface import User, Group
import aicompleter.session as session
from aicompleter.utils import Struct
from ...interface import CommandAuthority
from . import *

class FileInterface(Interface):
    '''
    File Interface for Autodone-AI
    Including File Read and Write
    '''
    def __init__(self, user: Optional[User] = None, id: Optional[uuid.UUID] = uuid.uuid4()):
        user = user or User(
            name="file",
            in_group="system",
            all_groups={"system","command"},
            support={"text","file"}
        )
        super().__init__(user,namespace="file",id=id)
        self.commands.add(
            Command(
                name='read',
                description='Read File',
                callback=self.cmd_read,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='File Path',tooltip='The file path to read')
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_readfile=True,
                )
            ),
            Command(
                name='write',
                description='Write File',
                callback=self.cmd_write,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='File Path',tooltip='The file path to write'),
                    'content': CommandParamElement('content', str, description='File Content',tooltip='The file content to write'),
                    'append': CommandParamElement('append', bool, description='Append',tooltip='Whether to append to the file'),
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_writefile=True,
                )
            ),
            Command(
                name='listdir',
                description='List Directory',
                callback=self.cmd_listdir,
                format=CommandParamStruct({
                    'path': CommandParamElement('path', str, description='Directory Path',tooltip='The directory path to list')
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
                in_interface=self,
                authority=CommandAuthority(
                    can_listdir=True,
                )
            ),
        )

    async def session_init(self, session:Session):
        ret = await super().session_init(session)
        # This data will be reuseable in other interfaces
        gdata = session.data['global']
        gdata['filesystem'] = FileSystem(session.config[self.namespace.name].get('root', 'workspace'))
        gdata['workspace'] = WorkSpace(gdata['filesystem'], '/')

    async def cmd_read(self, session:Session, message:Message) -> str:
        '''Command for reading file'''
        gdata = session.data['global']
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = gdata['filesystem']
        workspace:WorkSpace = gdata['workspace']
        file = workspace.get(path, session.id)
        if not file:
            raise FileNotFoundError(f'File {path} not found or no permission')
        if not file.type == Type.file:
            raise FileNotFoundError(f'File {path} is not a file')
        return file.read(session.id)
    
    async def cmd_write(self, session:Session, message:Message) -> str:
        '''Command for writing file'''
        data = self.getdata(session)
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = data['filesystem']
        workspace:WorkSpace = data['workspace']
        file = workspace.get(path, session.id)
        if not file:
            raise FileNotFoundError(f'File {path} not found or no permission')
        if not file.type == Type.File:
            raise FileNotFoundError(f'File {path} is not a file')
        if message.content.json['append']:
            return file.write_append(message.content.json['content'], session.id)
        return file.write(message.content.json['content'], session.id)

    async def cmd_listdir(self, session:Session, message:Message) -> list[str]:
        '''Command for listing directory'''
        data = self.getdata(session)
        path = message.content.json['path']
        if not path:
            raise ValueError('Path cannot be empty')
        path = normpath(path)
        filesystem:FileSystem = data['filesystem']
        workspace:WorkSpace = data['workspace']
        file = workspace.get(path, session.id)
        if not file:
            raise FileNotFoundError(f'Path {path} not found or no permission')
        if not file.type == Type.Folder:
            raise FileNotFoundError(f'Path {path} is not a directory')
        return file.listdir(session.id)
