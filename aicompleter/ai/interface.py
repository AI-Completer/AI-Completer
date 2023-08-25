'''
Implement the interface of the AI
Will generate a interface by the specified AI class
'''
from __future__ import annotations
import asyncio
import copy
import json

import uuid
from typing import Optional, TypeVar

from .. import *
from ..ai import ChatTransformer, Conversation, Transformer, Message as AIMessage
from ..config import Config
from ..interface import Command, Interface, User, CommandCall
from ..common import deserialize, serialize
from .. import Message, error

from . import *

# Chat Transformer class -> ChatInterface

class TransformerInterface(Interface):
    '''
    Transformer interface
    '''
    def __init__(self,*, ai:Transformer, namespace:Optional[str] = "transformer", user:Optional[User] = None, id:Optional[uuid.UUID] = None, config:Config = Config()):
        super().__init__(
            user=user or User(
                in_group="agent",
                all_groups={"agent","command"},
                support={"text"},
            ),
            namespace=namespace,
            id=id or uuid.uuid4(),
            config=config,
        )
        self.ai:Transformer = ai

class ChatInterface(TransformerInterface):
    '''
    Chat interface
    '''
    def __init__(self, *, ai: ChatTransformer, namespace:str, user:Optional[User] = None, id: Optional[uuid.UUID] = None, config:Config=Config()):
        super().__init__(ai=ai,namespace=namespace, user=user, id=id, config=config)
        self.ai.config.update(config)
        utils.typecheck(self.ai, ChatTransformer)

        if self.__class__ == ChatInterface:
            self.commands.add(
                Command(
                    cmd='ask',
                    description='Ask the AI',
                    expose=True,
                    in_interface=self,
                    to_return=True,
                    callback=self.ask,
                )
            )

    async def session_init(self, session: Session):
        # Not necessary
        self.getdata(session)['conversation'] = self.ai.new_conversation(user=session.id.hex)

    async def set_conversation(self, session: Session, conversation:Conversation):
        '''
        Set the conversation for ask command
        '''
        self.getdata(session)['conversation'] = conversation
    
    async def ask(self, session:Session, message:Message):
        '''
        Ask the AI
        '''
        conversation:Conversation = self.getdata(session)['conversation']
        
        async for i in self.ai.ask(message=ai.Message(
            content=message.content.text,
            role='user',
            user=session.id.hex,
        ), history=conversation):
            pass
        return i

    def __hash__(self):
        return hash(self.id)

    def getStorage(self, session: Session) -> Optional[dict]:
        conversation: Conversation = self.getdata(session)['conversation']
        return serialize(conversation)
    
    def setStorage(self, session: Session, data: dict):
        conversation = deserialize(data)
        self.getdata(session)['conversation'] = conversation
