import os
import uuid
from typing import Optional
from autodone import *
from autodone.interface import User, Group

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
        super().__init__(user, 'file', id)

    async def init(self):
        ...
        