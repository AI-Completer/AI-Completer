'''
Linux system (ssh) implement
'''

from typing import Optional
import uuid
from autodone import *
import paramiko

import autodone.session as session

class SSHInterface(Interface):
    '''
    Linux Terminal (SSH) Interface for Autodone-AI
    '''
    namespace:str = 'linux'
    def __init__(self, user: Optional[User] = None, id: Optional[uuid.UUID] = uuid.uuid4()):
        user = user or User(
            name="linux",
            in_group="system",
            all_groups={"system","command"},
            support={"text","image","audio","file"}
        )
        super().__init__(user,id=id)

    async def cmd_sh(self, session:Session, message:Message) -> tuple[str, str]:
        '''
        Command for running shell
        This will directly run the shell command
        '''
        client:paramiko.SSHClient = session.extra['interface.ssh.client']
        stdin, stdout, stderr = client.exec_command(message.content.json['cmd'])
        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')

    async def init(self):
        await super().init()
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
        with self.config.session() as config:
            config.require('ssh.host')
            config.setdefault('ssh.port', 22)
            config.require('ssh.username')
            if config.get('ssh.password', None) is None:
                config.require('ssh.private_key')
                config.require('ssh.private_key_passphrase')

    async def session_init(self, session: Session):
        await super().session_init(session)
        default_client = paramiko.SSHClient()
        default_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        default_client.connect(
            self.config.get('ssh.host'),
            port=self.config.get('ssh.port'),
            username=self.config.get('ssh.username'),
            password=self.config.get('ssh.password', None),
            key_filename=self.config.get('ssh.private_key', None),
            passphrase=self.config.get('ssh.private_key_passphrase', None),
        )
        session.extra['interface.ssh.client'] = default_client

