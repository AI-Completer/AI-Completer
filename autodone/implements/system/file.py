import os
import uuid
from typing import Optional
from autodone import *
from autodone.interface.base import Character

class FileInterface(Interface):
    '''
    File Interface for Autodone-AI
    Including File Read and Write
    '''
    namespace:str = 'file'
    def __init__(self, character: Optional[Character] = None, id: Optional[uuid.UUID] = uuid.uuid4()):
        character = character or Character(
            name="file",
            role=Role.SYSTEM,
        )
        super().__init__(character, 'file', id)

    async def init(self):
        '''
        Init the interface
        '''
        await super().init()
        self.commands.add(
            Command(
                cmd="read",
                description="Read file",
                callable_roles={Role.SYSTEM},
                overrideable=True,
            )
        )
        self.commands.add(
            Command(
                cmd="write",
                description="Write file",
                callable_roles={Role.SYSTEM},
                overrideable=True,
            )
        )
