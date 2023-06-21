'''
Linux system (ssh) implement
'''

from typing import Optional
import uuid
from aicompleter import *
import paramiko
from aicompleter.config import Config

import aicompleter.session as session

class SSHInterface(Interface):
    '''
    Linux Terminal (SSH) Interface for Autodone-AI
    '''
    namespace:str = 'linux'
    def __init__(self, id: Optional[uuid.UUID] = uuid.uuid4()):
        user = User(
            name="linux",
            in_group="system",
            all_groups={"system","command"},
            support={"text","image","audio","file"}
        )
        super().__init__(user,id=id)

        self.commands.add(
            Command(
                name='sh',
                description='Run Shell',
                func=self.cmd_sh,
                format=CommandParamStruct({
                    'cmd': CommandParamElement('cmd', str, description='Shell Command',tooltip='The shell command to run')
                }),
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
            )
        )

    async def cmd_sh(self, session:Session, message:Message) -> tuple[str, str]:
        '''
        Command for running shell
        This will directly run the shell command
        '''
        client:paramiko.SSHClient = session.extra['interface.ssh.client']
        stdin, stdout, stderr = client.exec_command(message.content.json['cmd'])
        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')

    async def session_init(self, session: Session):
        await super().session_init(session)
        
        cfg:Config = session.config[self.namespace]
        async with cfg.session() as config:
            config.require('ssh.host')
            config.setdefault('ssh.port', 22)
            config.require('ssh.username')
            if config.get('ssh.password', None) is None:
                config.require('ssh.private_key')
                config.require('ssh.private_key_passphrase')
        
        default_client = paramiko.SSHClient()
        default_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        default_client.connect(
            cfg.get('ssh.host'),
            port=cfg.get('ssh.port'),
            username=cfg.get('ssh.username'),
            password=cfg.get('ssh.password', None),
            key_filename=cfg.get('ssh.private_key', None),
            passphrase=cfg.get('ssh.private_key_passphrase', None),
        )
        session.extra['interface.ssh.client'] = default_client

