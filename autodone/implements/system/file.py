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
            support={"text","image","audio","file"}
        )
        super().__init__(user,id=id)

    async def cmd_read(self, session:Session, message:Message):
        '''Command for reading file'''
        if not Struct({
                'file': str,
            }).check(message.content.pure_text):
            raise error.FormatError(
                message=message,
                interface=self,
                content='Unrecognized format'
                )
        filepath = message.content.json['file']
        # TODO

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
                })
            )
        )

    async def session_init(self, session: Session):
        await super().session_init(session)
        session.extra['interface.file.filesystem'] = workspace.FileSystem(
            handler=session.in_handler, 
            root=self.config['root']
        )
