'''
Console Interface Implement
Provide a console interface for Autodone-AI
'''
import asyncio
import uuid
from typing import Optional

from autodone import error, interface, utils
from autodone.config import Config
from autodone.interface.base import User, Group
from autodone.session import Message, Session
from autodone.session.base import MultiContent


class ConsoleInterface(interface.Interface):
    '''
    Console Interface
    Interactive with user in console
    '''
    namespace:str = "console"
    def __init__(self,id: uuid.UUID = uuid.uuid4(), user:Optional[User] = None):
        user = user or User(
            name="console",
            in_group="user",
        )
        super().__init__(user,id = id)

    async def ask_user(self, session:Session, message:Message):
        '''
        Ask user for input
        '''
        await utils.aprint(f"The {message.src_interface.user.name} ask you: {message.content.text}")
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
        await utils.aprint(f"The {message.src_interface.user.name} reply you: {message.content.text}")

    async def init(self):
        '''
        Init the interface
        '''
        await super().init()
        self.commands.add(
            interface.Command(
                cmd="ask",
                description="Ask user for question",
                callable_groups={"system", "agent"},
                overrideable=True,
                in_interface=self,
                callback=self.ask_user,
            ),
            interface.Command(
                cmd="reply",
                description="Reply to user in console",
                callable_groups={"system", "agent"},
                overrideable=True,
                in_interface=self,
                callback=self.reply,
            )
        )
