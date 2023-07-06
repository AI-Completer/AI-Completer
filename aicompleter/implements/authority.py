'''
This is an authority module, which is used to manage the authority of the user.
'''
from typing import Any

import aicompleter.session as session
from .. import *
from utils import Struct

def is_enable(srctext:Any) -> bool:
    if srctext in ('enable', 'true', 'True', '1', True, 'yes', 'y', 't'):
        return True
    if srctext in ('disable', 'false', 'False', '0', False, 'no', 'n', 'f'):
        return False
    raise ValueError(f"Cannot convert {srctext} to bool")

class AuthorInterface(Interface):
    '''
    Authority Interface
    This will inject into the command call to check the authority of the user
    '''
    def __init__(self) -> None:
        super().__init__(
            User(name='authority',description='Authority Interface',in_group='system'),
            namespace='authority',
        )

    async def hook(self, event:events.Event, session: Session, message: Message) -> None:
        '''
        Hook function
        '''
        cfg = self.getconfig(session)
        trigger_level:int = cfg['level']
        author_cmd:str = cfg['authority']['cmd']
        author_format:str = cfg['authority']['format']

        cmd = session.in_handler.get_cmd(message.cmd, message.src_interface, message.dest_interface)

        if cmd.authority.get_authority_level() < trigger_level:
            # Not triggered
            return
        if cmd.cmd == author_cmd:
            # Can not trigger self
            return 
        enabled = None
        while enabled == None:
            ret = await session.asend(
                Message(
                    src_interface=self.interface,
                    cmd=author_cmd,
                    content = author_format.format(
                        src=message.src_interface.user.name,
                        cmd=cmd.cmd,
                        param=message.content.text,
                        level=cmd.authority.get_authority_level(),
                    ),
                    last_message = message,
                )
            )
            try:
                enabled = is_enable(ret)
            except ValueError:
                pass
        return not enabled

    async def session_init(self, session: Session) -> None:
        self.getconfig(session).setdefault({
            'level': 15,
            'authority': {
                'cmd': 'ask',
                'format': '{"content": "The {src} want to use {cmd}, the parameter is {param}, do you allow it?", "options": ["(y)es", "(n)o"]}',
            }
        })
        if Struct({
            'level': int,
            'authority': {
                'cmd': str,
                'format': str,
            }
        }).check(self.getconfig(session)) == False:
            raise ValueError(f"Config error: {self.getconfig(session)}")
        
        session.in_handler.on_call.add_callback(self.hook)    
        return await super().session_init(session)

    async def session_final(self, session: Session) -> None:
        session.in_handler.on_call.callbacks.remove(self.hook)
        return await super().session_final(session)

