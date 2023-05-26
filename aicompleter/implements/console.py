'''
Console Interface Implement
Provide a console interface for Autodone-AI
'''
import uuid

from aicompleter import interface, utils
from aicompleter.interface.base import User, Group
from aicompleter.session import Message, Session


class ConsoleInterface(interface.Interface):
    '''
    Console Interface
    Interactive with user in console
    '''
    namespace:str = "console"
    def __init__(self,id: uuid.UUID = uuid.uuid4()):
        user = User(
            name="console",
            in_group="user",
            all_groups={"user","command"},
        )
        super().__init__(user,id = id)

        self.commands.add(
            interface.Command(
                cmd="ask",
                description="Ask user for question",
                callable_groups={"system", "command", "agent"},
                overrideable=True,
                in_interface=self,
                callback=self.ask_user,
            ),
            interface.Command(
                cmd="reply",
                description="Reply to user in console",
                callable_groups={"system", "command"},
                overrideable=True,
                in_interface=self,
                callback=self.reply,
            )
        )

    async def ask_user(self, session:Session, message:Message):
        '''
        Ask user for input
        '''
        await utils.aprint(f"The {message.src_interface.user.name if message.src_interface else '[Unknown]'} ask you: {message.content.text}")
        return await utils.ainput("Please input your answer: ")

    async def reply(self, session:Session, message:Message):
        '''
        Reply to console interface
        '''
        await utils.aprint(f"The {message.src_interface.user.name} reply you: {message.content.text}")