import asyncio
from typing import Optional
import uuid

from autodone import *
from autodone.config import Config
from autodone.implements.openai.api import EnterPoint
from autodone.interface.base import Character
import api
from autodone.utils import Struct

class OPENAI_ChatInterface(Interface):
    '''
    OpenAI API Chat Interface
    '''
    def __init__(self, character: Character, id: uuid.UUID = ...):
        # Require the api key
        super().__init__(character, id)
        
        

    async def chat(self, session: Session, message: Message):
        '''
        Chat with User
        '''
        if message.content.text == "":
            raise ValueError("Empty message")
        # Construct the json data
        param = api.ChatParameters()
        param.from_json(self.config['chat'])
        history:list[api.Message] = session.extra['interface.openaichat.history']
        param.messages = history + [
            api.Message(
                role='user',
                content=message.content.text,
                name=message.src_interface.character.name,
                )
            ]
        enterpoiot:EnterPoint = session.extra['interface.openaichat.enterpoint']
        enterpoiot.proxy = self.proxy
        try:
            ret = await enterpoiot.chat(param)
        except Exception as e:
            raise e
        if ret is None:
            raise ValueError("Empty response")
        # Construct the message
        nmessage = ret['choices'][0]['message']
        param.messages.append(
            api.Message(
                role='system',
                content=nmessage,
                name=self.character.name,
            )
        )
        session.extra['interface.openaichat.history'] = param.messages
        session.extra['interface.openaichat.enterpoint'] = enterpoiot
        session.send(
            Message(
                src_interface=self,
                dest_interface=message.src_interface,
                cmd='ask',
                last_message=message,
                content=MultiContent(nmessage['text']),
            )
        )

    async def init(self, session: Session):
        '''
        Init the interface
        '''
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
            config.require("api_key")
        
        self.proxy:Optional[dict] = None
        if config.has('interface.openaichat.proxy'):
            proxy_config = config['interface.openaichat.proxy']
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
                cmd="chat",
                description="Chat with OpenAI API",
                callable_roles={Role.USER},
                overrideable=True,
                in_interface=self,
                call=self.chat,
            )
        )
        session.extra['interface.openaichat.history'] = []
        session.extra['interface.openaichat.enterpoint'] = api.EnterPoint(self.config['api_key'])


