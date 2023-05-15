'''
Console Interface Implement
Provide a console interface for Autodone-AI
'''
import asyncio
import uuid
from typing import Optional

from autodone import error, interface, utils
from autodone.config import Config
from autodone.interface.base import Character, Role
from autodone.session import Message, Session
from autodone.session.base import MultiContent


class ConsoleInterface(interface.Interface):
    '''
    Console Interface
    Interactive with user in console
    '''
    namespace:str = "console"
    def __init__(self,id: uuid.UUID = uuid.uuid4(), character: Optional[Character] = None):
        character = character or Character(
            name="console",
            role=Role.USER,
        )
        super().__init__(character,id = id)

    async def ask_user(self, session:Session, message:Message):
        '''
        Ask user for input
        '''
        await utils.aprint(f"The {message.src_interface.character.name} ask you: {message.content.text}")
        ret = await utils.ainput("Please input your answer: ")
        new_message = Message(
            content=MultiContent(ret),
            session=session,
            cmd="chat",
            src_interface=self,
            last_message=message,
        )
        session.in_handler.call_soon(session, new_message)

    async def reply(self, session:Session, message:Message):
        '''
        Reply to console interface
        '''
        await utils.aprint(f"The {message.src_interface.character.name} reply you: {message.content.text}")

    async def init(self):
        '''
        Init the interface
        '''
        await super().init()
        self.commands.add(
            interface.Command(
                cmd="ask",
                description="Ask user for question",
                callable_roles={Role.SYSTEM, Role.AGENT},
                overrideable=True,
                in_interface=self,
                callback=self.ask_user,
            ),
            interface.Command(
                cmd="reply",
                description="Reply to user in console",
                callable_roles={Role.SYSTEM, Role.AGENT},
                overrideable=True,
                in_interface=self,
                callback=self.reply,
            )
        )
