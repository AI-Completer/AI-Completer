import json
import uuid
from typing import Optional

from aicompleter import *
from aicompleter.ai import ChatInterface, ChatTransformer, Conversation
from aicompleter.interface import Command, Commands
from aicompleter.session import Message

class CmdTranslator(ChatInterface):
    '''
    Command Translator
    Translate the natural language to command
    '''
    def __init__(self, *, config:Config = Config(), ai: ChatTransformer, user: Optional[User] = None, id: Optional[uuid.UUID] = None):
        super().__init__(ai=ai,namespace='cmd-translator', user=user, id=id, config=config)
        self.commands.add(
            Command(
                cmd='translate',
                description='Translate the natural language to command',
                expose=True,
                in_interface=self,
                callback=self.cmd_translate,
            )
        )

    async def cmd_translate(self, session: Session, message: Message):
        '''
        Translate the natural language to command
        '''
        command_table = "\n".join(
            f'|{command.cmd}|{command.format.json_text}|{command.description}|'
            for command in session.in_handler.get_executable_cmds(self._user)
        )
        ret = await self.ai.generate_text(
            conversation=Conversation(
                messages=[
                    Message(
                        content=f'''
You are a command translator. Your task is to translate the natural language to commands.
Here is the commands table:
|name|parameter struct|description|
|-|-|-|
{command_table}
What the user said is the task.
You need to reply with the json format below(important!):
[{{"cmd": <name>, "param": <parameters>, "async": <bool>"}}]
If you think the command is unable to execute, use the specific command json element {{"executable": false}}, and don't translate the following commands.
If you think the command need to reply to handle, use the specific command json element {{"cmd": <name>, reply": true}}, and don't translate the following commands.
If you think the command need more details, use the specific command json element {{"cmd": <name>, "detail": true}}, and don't translate the following commands.
For example:
[{{"cmd":"echo", "param":"Hello?", "async": true}},{{"cmd":"ask", "reply": true}}]
Do not use abstract natural language to execute the system command unless it inform you that you can do it.
Do not reply with anything else.
                        ''',
                        role='system',
                    )
                ]
            )
        )

        try:
            ret = json.loads(ret)
        except json.JSONDecodeError:
            raise error.AI_InvalidJSON(content=ret, interface=self, message=message)
        
        if not isinstance(ret, list):
            raise error.AI_InvalidJSON(content=ret, interface=self, message=message, detail='The json is not a list')
        
        for dictcheck in ret:
            if not isinstance(dictcheck, dict):
                raise error.AI_InvalidJSON(content=ret, interface=self, message=message, detail='The json is not a list of dict')
            
            if set(dictcheck.keys()) not in {{'cmd','param','async'},{'cmd','reply'},{'cmd','detail'},{"executable"}}:
                raise error.AI_InvalidJSON(content=ret, interface=self, message=message, detail='The json is not a list of dict with specific keys')
        
        return ret

    async def cmd_execute(self, session: Session, message: Message):
        '''
        Execute the command
        The command should be translated by cmd_translate
        '''
        data = EnhancedDict(message.content.json)
        if 'cmd' not in data:
            raise error.ParamRequired(data, detail='Missing command')
        data.setdefault('param', '')
        data.setdefault('async', False)
        cmds = Commands(session.in_handler.get_executable_cmds(self._user))
        if 'cmd' not in cmds:
            raise error.NotFound(data, detail='Command not found')
        cmd = cmds['cmd']

        new_message = Message(
            content=MultiContent(
                data['param'],
            ),
            session=session,
            src_interface=self,
            dest_interface=cmd.in_interface,
            last_message=message,
        )
        if data['async']:
            session.in_handler.send(
                session, 
                new_message
            )
            return 
        return await cmd.call(session, new_message)
