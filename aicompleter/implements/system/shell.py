import os
from ... import *
from asyncio import subprocess

class ShellConfig(ConfigModel):
    '''
    Shell config
    '''
    pipe_encoding: str = 'utf-8'
    if os.name == 'nt':
        # May be a difficlut problem to get the page code of the console
        # There we use gbk as default
        pipe_encoding: str  = 'gbk'

class ShellInterface(Interface):
    '''
    Shell interface

    This interface is used to interact with the shell, using system commands directly.
    '''
    cmdreg: Commands = Commands()
    configFactory = ShellConfig
    
    namespace: BaseNamespace = BaseNamespace(
        name='shell',
        description='Shell commands',
    )

    @cmdreg.register("shell", "run a shell command", format={'cmd': 'command to run'},
                     authority=CommandAuthority(can_execute=True))
    async def shell(self, cmd: str, config: ShellConfig):
        '''
        Run a shell command

        :param cmd: command to run
        '''
        proc = await subprocess.create_subprocess_shell(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stderr == b'':
            return stdout.decode(config.pipe_encoding)
        return {
            'stdout': stdout.decode(config.pipe_encoding),
            'stderr': stderr.decode(config.pipe_encoding)
        }
