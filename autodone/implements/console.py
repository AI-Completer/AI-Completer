'''
Console Interface Implement
Provide a console interface for Autodone-AI
'''
import asyncio
import uuid
from autodone import interface, error, utils
from autodone.session import Session, Message
from autodone.interface.base import Character, Role

class ConsoleInterface(interface.Interface):
    '''
    Console Interface
    Interactive with user in console
    '''
    def __init__(self, character: Character, id: uuid.UUID = uuid.uuid4()):
        super().__init__(character, id)

    async def ask_user(self, session:Session, message:Message):
        '''
        Ask user for input
        '''
        await utils.aprint(f"The {message.src_interface.character.name} ask you: {message.content.text}")
        ret = await utils.ainput("Please input your answer:")
        new_message = Message(
            content=ret,
            session=session,
            cmd="reply",
            src_interface=self,
            dest_interface=message.src_interface,
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
        self.commands.add(
            interface.Command(
                cmd="ask",
                description="Ask user for question",
                callable_roles={Role.SYSTEM, Role.AGENT},
                overrideable=True,
                in_interface=self,
                call=self.ask_user,
            ),
            interface.Command(
                cmd="reply",
                description="Reply to user in console",
                callable_roles={Role.SYSTEM, Role.AGENT},
                overrideable=True,
                in_interface=self,
                call=self.reply,
            )
        )
