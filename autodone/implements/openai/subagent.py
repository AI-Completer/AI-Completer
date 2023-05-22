'''
Sub agent is a agent that is used to train a subtask.
Usually, it is used to translate a normal language command to json data,
which can be recognized by python code.
'''

import json
from typing import Optional
import uuid
from autodone import *
from autodone.implements.openai import api
import autodone.session as session
from autodone.utils import Struct

class OpenAISubAgentInterface(Interface):
    '''
    OpenAI API Sub Agent Interface
    '''
    namespace:str = "subagent"
    def __init__(self, user:Optional[User] = None, id: Optional[uuid.UUID] = None):
        super().__init__(
            user=user or User(
                name="openaisubagent",
                in_group="subagent",
                all_groups={"agent","subagent"},
                support={"text"},
            ),
            id=id or uuid.uuid4(),
        )

    async def cmd_sinchat(self, session: Session, message: Message):
        '''
        Chat without history
        '''
        if message.content.text == "":
            raise ValueError("Empty message")
        # Construct the description
        command_str = "|command|descrption|data struct|\n"\
            "|-|-|-|\n" + \
            '\n'.join([
            '|' + i.cmd + '`|' + i.description + '|' + i.format.json_description() if i.format else '<content>' + '|'
            for i in session.in_handler.get_cmds_by_group('command')
        ])
        # Construct the json data
        param = api.ChatParameters()
        param.from_json(self.config['chat'])
        param.messages = [
            api.Message(
                role='system',
                content=self.config['sys.prompt'] + f'\n{command_str}',
            ),
            api.Message(
                role='user',
                content=message.content.text,
            ),
            api.Message(
                role='system',
                content='Reply in this json format:\n' + \
                    '[{"command":<command>, "data":<data>},<other commands(if existed)>]'
            )
        ]
        enterpoint:api.EnterPoint = session.extra['interface.subagent.enterpoint']
        try:
            result = await enterpoint.chat(param)
        except Exception as e:
            raise e
        
        ret = result['choices'][0]['text']['content']
        try:
            ret = json.loads(ret)
        except:
            raise ValueError("Invalid json data")
        
        res = []
        for i in ret:
            if not Struct({
                'command': str,
                'data': dict,
            }).check(i):
                raise ValueError("Invalid json data")
            command = i['command']
            data = i['data']
            res.append(await session.asend(command, session, Message(
                src_interface=self,
                content=MultiContent(data)
            )))
        res.remove(None)
        return res

    async def session_init(self, session: Session):
        await super().session_init(session)
        session.extra['interface.subagent.enterpoint'] = api.EnterPoint(self.config['chat.api_key'])

    async def init(self):
        await super().init()
        with self.config.session() as config:
            config.setdefault("chat.model", "gpt-3.5-turbo-0301")
            config.setdefault("chat.temperature", None)
            config.setdefault("chat.max_tokens", None)
            config.setdefault("chat.top_p", None)
            config.setdefault("chat.frequency_penalty", None)
            config.setdefault("chat.presence_penalty", None)
            config.setdefault("chat.stop", None)
            config.setdefault("chat.n", None)
            config.setdefault("chat.logit_bias", None)
            config.setdefault("chat.stream", None)
            config.setdefault("chat.user", None)
            config.setdefault("sys.prompt", "You are ChatGPT created by OpenAI. Your task is to translate user's command to json data.")
            config.setdefault("sys.max_history", None)
            config.setdefault("sys.max_input_tokens", 2048)
            config.require("openai.api-key")

        # Proxy
        self.proxy:Optional[dict] = None
        if config.has('proxy'):
            proxy_config = config['proxy']
            if isinstance(proxy_config, str):
                self.proxy = {
                    'http':proxy_config,
                    'https':proxy_config,
                    'socks5':proxy_config,
                }
            else:
                if not Struct({
                    'http':str,
                    'https':str,
                    'socks5':str,
                }).check(proxy_config):
                    raise ValueError("Invalid proxy")
                self.proxy = proxy_config

        self.commands.add(
            Command(
                name='single-chat',
                description='Chat without history',
                func=self.cmd_sinchat,
                to_return=True,
                force_await=True,
                callable_groups={'system','agent'},
            )
        )
