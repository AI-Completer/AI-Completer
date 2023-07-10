'''
Console Interface Implement
Provide a console interface for Autodone-AI
'''
import uuid

from aicompleter import interface, utils
from aicompleter.config import Config
from aicompleter.interface.base import User, Group
from aicompleter.interface.command import CommandParamElement, CommandParamStruct
from aicompleter.session import Message, Session

class ConsoleInterface(interface.Interface):
    '''
    Console Interface
    Interactive with user in console
    '''
    def __init__(self, config:Config = Config(),id: uuid.UUID = uuid.uuid4()):
        user = User(
            name="console",
            in_group="user",
            all_groups={"user","command"},
        )
        super().__init__(user,id = id, namespace="console", config=config)

        self.commands.add(
            interface.Command(
                cmd="ask",
                description="Ask or reply user.",
                callable_groups={"system", "command", "agent"},
                overrideable=True,
                in_interface=self,
                callback=self.cmd_ask,
                format=CommandParamStruct({
                    'content': CommandParamElement('content', str, description="Content to ask or reply."),
                })
            ),
            interface.Command(
                cmd="echo",
                description="Show a message to the user. User will not be able to reply.",
                callable_groups={"system", "command"},
                overrideable=True,
                in_interface=self,
                callback=self.cmd_echo,
                format=CommandParamStruct({
                    'content': CommandParamElement('content', str, description="Content to show."),
                })
            )
        )

    async def cmd_ask(self, session:Session, message:Message):
        '''
        Ask user for input
        '''
        await utils.aprint(f"The {message.src_interface.user.name if message.src_interface else '[Unknown]'} ask you: {message.content.json['content']}")
        return await utils.ainput(">>> ")

    async def cmd_echo(self, session:Session, message:Message):
        '''
        Reply to console interface
        '''
        await utils.aprint(f"The {message.src_interface.user.name} reply you: {message.content.json['content']}")
