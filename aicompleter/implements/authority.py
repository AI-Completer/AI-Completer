'''
This is an authority module, which is used to manage the authority of the user.
'''
from typing import Any
import uuid

import aicompleter.session as session
from .. import *
from ..utils import Struct

class AuthorInterface(Interface):
    '''
    Authority Interface
    This will inject into the command call to check the authority of the user
    '''
    def __init__(self, config:Config = Config(), id:uuid.UUID = uuid.uuid4()) -> None:
        super().__init__(
            user = User(name='authority',description='Authority Interface',in_group='system'),
            namespace='authority',
            config= config,
            id = id,
        )
        self.config.setdefault({
            'level': 15,
            'authority': {
                'cmd': 'ask',
                'format': '{{"content": "The {src} want to use {cmd}, the parameter is {param}, do you allow it?(y/n)"}}',
            }
        })

    async def hook(self, event:events.Event, session: Session, message: Message) -> None:
        '''
        Hook function
        '''
        cfg = self.getconfig(session)
        trigger_level:int = cfg['level']
        author_cmd:str = cfg['authority']['cmd']
        author_format:str = cfg['authority']['format']

        cmd = session.in_handler.get_cmd(message.cmd, message.dest_interface, message.src_interface)
        if cmd == None:
            # Unknown command
            return

        if cmd.authority.get_authority_level() < trigger_level:
            # Not triggered
            return
        if cmd.cmd == author_cmd:
            # Can not trigger self
            return 
        
        self.logger.debug(f"Authority triggered, cmd={cmd.cmd}, level={cmd.authority.get_authority_level()}")
        
        ret = await session.asend(
            Message(
                cmd=author_cmd,
                src_interface=self,
                content = author_format.format(
                    src=message.src_interface.user.name,
                    cmd=cmd.cmd,
                    param=message.content.text.replace("\\", "\\\\").replace('"', '\\"'),
                    level=cmd.authority.get_authority_level(),
                ),
                last_message = message,
            )
        )
        try:
            enabled = utils.is_enable(ret)
        except ValueError:
            raise error.AuthorityError(
                ret,
                session = session,
                message = message,
            )
        
        if not enabled:
            raise error.Interrupted(
                'user authority denied',
                session = session,
                message = message,
            )
        
        # Not stop the propagation
        return False

    async def session_init(self, session: Session) -> None:
        if Struct({
            'level': int,
            'authority': {
                'cmd': str,
                'format': str,
            }
        }).check(self.getconfig(session)) == False:
            raise ValueError(f"Config error: {self.getconfig(session)}")
        
        session.on_call.add_callback(self.hook)

    async def session_final(self, session: Session) -> None:
        session.on_call.callbacks.remove(self.hook)

