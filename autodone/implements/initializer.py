import asyncio
from enum import Flag
import json
import uuid
from typing import Any, Optional

from autodone import error, interface
from autodone.interface.base import Character, Interface, Role
from autodone.session import Message, Session
from autodone.session.base import MultiContent
from autodone.utils import Struct


class InitInterface(interface.Interface):
    '''
    Initializer Interface
    Only used for initializing the session request
    '''
    namespace: str = "initializer"
    def __init__(self, id: uuid.UUID = uuid.uuid4(), character: Optional[Character] = None):
        character = character or Character(
            name="initializer",
            role=Role.SYSTEM,
            support_text=False,
        )
        super().__init__(character,id = id)

        self.__init_called:bool = False
        '''Whether cmd_init is called'''

    async def cmd_init(self, session:Session, message:Message):
        '''
        Init the session
        '''
        if self.__init_called is True:
            raise error.PermissionDenied(
                message.cmd,
                interface=self,
                session=session,
                content='Initializer can only be called once'
            )
        try:
            data = json.loads(message.content.text)
        except json.JSONDecodeError:
            raise error.MessageNotUnderstood(message, session)
        if not Struct({
            "interface-name":str,
            "command":str,
            "data":Any,
        }).check(data):
            raise error.MessageNotUnderstood(message, self)
        for i in session.in_handler:
            if i.character.name == data["interface-name"]:
                break
        if i.character.name != data["interface-name"]:
            raise error.NotFound("Interface Not Found",message=message, interface=self, data=data)
        if not i.commands.has(data["command"]):
            raise error.MessageNotUnderstood(message, self)
        cmd = i.commands.get(data["command"])
        if not self.character.role in cmd.callable_roles:
            raise error.PermissionDenied(message, self)
        message.cmd = cmd.cmd
        message.content = MultiContent(data["data"])
        message.src_interface = self
        message.dest_interface = i
        self.__init_called = True
        session.in_handler.call_soon(session, message)

    async def cmd_reply(self, session:Session, message:Message):
        '''
        Reply to initializer
        The will call the 'reply' command of the handler
        '''
        new_message:Message = Message(
            content=message.content,
            session=session,
            cmd="chat",
            src_interface=self,
            last_message=message,
        )
        session.in_handler.call_soon(session, new_message)

    async def init(self):
        '''
        Initialize this interface
        Add commands for first call to handler
        '''
        await super().init()
        self.commands.add(
            interface.Command(
                cmd="init",
                description="Initialize the session",
                callable_roles=set(),
                # No one can call this command, it's only used for initializing
                # and pass the message to the right interface
                overrideable=True,
                expose=True,
                in_interface=self,
                callback=self.cmd_init,
            ),
            interface.Command(
                cmd="reply",
                description="Reply to initializer",
                callable_roles={Role.SYSTEM, Role.USER},
                overrideable=True,
                expose=False,
                in_interface=self,
                callback=self.cmd_reply,
            )
        )
