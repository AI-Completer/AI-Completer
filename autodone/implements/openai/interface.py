import asyncio
import uuid
from typing import Optional

from autodone import *
from autodone.config import Config
from autodone.implements.openai.api import EnterPoint
from autodone.interface import Command, Interface, User, Group
from autodone.session import Message, MultiContent, Session
from autodone.utils import Struct

from . import api

class OpenaichatInterface(Interface):
    '''
    OpenAI API Chat Interface
    '''
    namespace:str = "openaichat"
    def __init__(self, user:Optional[User] = None, id: Optional[uuid.UUID] = None):
        super().__init__(
            user=user or User(
                name="openaichat",
                in_group="agent",
                in_groups={"agent","command"},
                support={"text"},
            ),
            id=id or uuid.uuid4(),
        )

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
                # name=message.src_interface.character.name,
                )
            ]
        if self.config['sys.prompt'] is not None:
            param.messages.insert(0, api.Message(
                    role='system',
                    content=self.config['sys.prompt'],
                    ))
        if self.config['sys.max_history'] is not None:
            param.messages = api.limitMessageToken(
                self.config['chat.model'],
                param.messages,
                self.config['sys.max_input_tokens']
            )
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
                role=nmessage['role'],
                content=nmessage['content'],
            )
        )
        if self.config['sys.prompt'] is not None:
            param.messages.pop(0) # Remove the first message
        if self.config['sys.max_history'] is not None:
            if len(param.messages) > self.config['sys.max_history']:
                param.messages = param.messages[-self.config['sys.max_history']:]
        session.extra['interface.openaichat.history'] = param.messages
        session.extra['interface.openaichat.enterpoint'] = enterpoiot
        ret = await session.asend(
            Message(
                src_interface=self,
                cmd='ask',
                last_message=message,
                content=MultiContent(nmessage['content']),
            )
        )
        # Call Self
        session.send(
            Message(
                src_interface=self,
                cmd='chat',
                last_message=message,
                content=MultiContent(ret),
            )
        )

    async def session_init(self, session: Session):    
        '''
        Init the session
        '''    
        session.extra['interface.openaichat.history'] = []
        enterpoint = api.EnterPoint(self.config['api-key'])
        enterpoint.proxy = self.proxy
        session.extra['interface.openaichat.enterpoint'] = enterpoint
        

    async def init(self):
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
            config.setdefault("sys.prompt", "You are ChatGPT created by OpenAI. Your task is to chat with user and assist him.")
            config.setdefault("sys.max_history", None)
            config.setdefault("sys.max_input_tokens", 2048)
            config.require("api-key")
        
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
                cmd="chat",
                description="Chat with OpenAI API",
                callable_groups={"user","system","agent"},
                overrideable=True,
                in_interface=self,
                callback=self.chat,
            )
        )
