'''
Implement the interface of the AI
Will generate a interface by the specified AI class
'''
from __future__ import annotations
from typing import (
    Optional,
    TypeVar,
)
import uuid
from aicompleter import *
from aicompleter.ai import Transformer, ChatTransformer, Conversation
from aicompleter.config import Config
from aicompleter.interface import Command

from aicompleter.interface import Interface
from aicompleter.interface import User
import aicompleter.session as session
from . import *

# Chat Transformer class -> ChatInterface

class TransformerInterface(Interface):
    '''
    Transformer interface
    '''
    def __init__(self,*, ai:Transformer, user:Optional[User] = None, id:Optional[uuid.UUID] = None):
        super().__init__(
            user=user or User(
                name=ai.name,
                in_group="agent",
                all_groups={"agent","command"},
                support={"text"},
            ),
            id=id or uuid.uuid4()
        )
        self.ai:Transformer = ai

class ChatInterface(TransformerInterface):
    '''
    Chat interface
    '''
    def __init__(self, *, ai: ChatTransformer, namespace:str, user:Optional[str] = None, id: Optional[uuid.UUID] = None):
        super().__init__(ai=ai, user=user, id=id)
        self.namespace = namespace

        self.commands.add(
            Command(
                cmd='ask',
                description='Ask the AI',
                expose=True,
                in_interface=self,
                to_return=True,
                force_await=True,
                callback=self.cmd_ask,
            )
        )

    async def session_init(self, session: Session):
        await super().session_init(session)
        session.extra[f'{self.namespace}.conversation'] = ai.Conversation(
            messages=[
                ai.Message(
                    content=session.config[self.namespace].get('sys.prompt',"You are ChatGPT, a chatbot.\nYour task is to assist the user."),
                    role='system',
                )
            ]
        )
    
    async def cmd_ask(self, session:Session, message:Message):
        '''
        Ask the AI
        '''
        self.ai.config = session.config[self.namespace]
        conversation:Conversation = session.extra[f'{self.namespace}.conversation']
        conversation = await self.ai.ask(history=conversation,message=ai.Message(
            content=message.content.text,
            role='user',
            user=session.id.hex,
        ))
        session.extra[f'interface.{self.namespace}.conversation'] = conversation
        return conversation.messages[-1].content

    
