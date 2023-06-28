import os
import uuid
from typing import Optional
from aicompleter import *
from aicompleter.interface import User, Group
import aicompleter.session as session
from aicompleter.utils import Struct
import workspace

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
                func=self.cmd_read,
                format=CommandParamStruct({
                    'file': CommandParamElement('file', str, description='File Path',tooltip='The file path to read')
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
            )
        )

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
        ws:workspace.WorkSpace = session.data[f'{self.namespace.name}.workspace']
        fs:workspace.FileSystem = session.data[f'{self.namespace.name}.filesystem']
        if ws.check(filepath):
            return fs.get(filepath).read(self.user)
        else:
            raise error.PermissionDenied(
                message=message,
                interface=self,
                content='Not allowed for reading file out of workspace'
            )

    async def session_init(self, session: Session):
        await super().session_init(session)
        session.config[self.namespace.name].setdefault('root','./workspace')
        thisconfig = session.config[self.namespace.name]
        session.data[f'{self.namespace.name}.filesystem'] = workspace.FileSystem(
            handler=session.in_handler, 
            root=thisconfig['root']
        )
        session.data[f'{self.namespace.name}.workspace'] = workspace.WorkSpace(
            path=thisconfig['root'],
        )
