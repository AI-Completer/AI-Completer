import os
import uuid
from typing import Optional
from autodone import *
from autodone.interface import User, Group
import autodone.session as session
from autodone.utils import Struct
import workspace

class FileInterface(Interface):
    '''
    File Interface for Autodone-AI
    Including File Read and Write
    '''
    namespace:str = 'file'
    def __init__(self, user: Optional[User] = None, id: Optional[uuid.UUID] = uuid.uuid4()):
        user = user or User(
            name="file",
            in_group="system",
            all_groups={"system","command"},
            support={"text","image","audio","file"}
        )
        super().__init__(user,id=id)

    async def cmd_read(self, session:Session, message:Message) -> str:
        '''Command for reading file'''
        if not Struct({
                'file': str,
            }).check(message.content.json):
            raise error.FormatError(
                message=message,
                interface=self,
                content='Unrecognized format'
                )
        filepath = message.content.json['file']
        ws:workspace.WorkSpace = session.extra['interface.file.workspace']
        fs:workspace.FileSystem = session.extra['interface.file.filesystem']
        if ws.check(filepath):
            return fs.get(filepath).read(self.user)
        else:
            raise error.PermissionDenied(
                message=message,
                interface=self,
                content='Not allowed for reading file out of workspace'
            )

    async def init(self):
        await super().init()
        self.config.setdefault('root', './workspace')
        self.commands.add(
            Command(
                name='read',
                description='Read File',
                func=self.cmd_read,
                format=CommandParamStruct({
                    'file': CommandParamElement('file', str, description='File Path',tooltip='The file path to read')
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
            )
        )

    async def session_init(self, session: Session):
        await super().session_init(session)
        session.extra['interface.file.filesystem'] = workspace.FileSystem(
            handler=session.in_handler, 
            root=self.config['root']
        )
        session.extra['interface.file.workspace'] = workspace.WorkSpace(
            path=self.config['root'],
        )
