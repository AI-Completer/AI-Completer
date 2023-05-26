import asyncio
import uuid
from typing import Optional

from aicompleter import *
from aicompleter.config import Config
from aicompleter.implements.openai.api import EnterPoint
from aicompleter.interface import Command, Interface, User, Group
from aicompleter.session import Message, MultiContent, Session
from aicompleter.utils import Struct

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
                all_groups={"agent","command"},
                support={"text"},
            ),
            id=id or uuid.uuid4(),
        )
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

    async def chat(self, session: Session, message: Message):
        '''
        Chat with User
        '''
        cfg = session.config[self.namespace]
        if message.content.text == "":
            raise ValueError("Empty message")
        # Construct the json data
        param = api.ChatParameters()
        param.from_json(cfg['chat'])
        history:list[api.Message] = session.extra['interface.openaichat.history']
        param.messages = history + [
            api.Message(
                role='user',
                content=message.content.text,
                # name=message.src_interface.character.name,
                )
            ]
        if cfg['sys.prompt'] is not None:
            param.messages.insert(0, api.Message(
                    role='system',
                    content=cfg['sys.prompt'],
                    ))
        if cfg['sys.max_history'] is not None:
            param.messages = api.limitMessageToken(
                cfg['chat.model'],
                param.messages,
                cfg['sys.max_input_tokens']
            )
        enterpoiot:EnterPoint = session.extra['interface.openaichat.enterpoint']
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
        if cfg['sys.prompt'] is not None:
            param.messages.pop(0) # Remove the first message
        if cfg['sys.max_history'] is not None:
            if len(param.messages) > cfg['sys.max_history']:
                param.messages = param.messages[-int(cfg['sys.max_history']):]
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
                dest_interface=self,
                cmd='chat',
                last_message=message,
                content=MultiContent(ret),
            )
        )

    async def session_init(self, session: Session):    
        '''
        Init the session
        '''    
        await super().session_init(session)
        
        cfg:Config = session.config[self.namespace]
        async with cfg.session() as config:
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
            config.require("openai.api-key")
        
        proxy_config = None
        if cfg.has('proxy'):
            proxy_config = config['proxy']
            if isinstance(proxy_config, str):
                cfg['proxy'] = {
                    'http':proxy_config,
                    'https':proxy_config,
                    'socks5':proxy_config,
                }
        
        session.extra['interface.openaichat.history'] = []
        enterpoint = api.EnterPoint(cfg['openai.api-key'])
        if cfg['proxy.http']:
            enterpoint.proxy = cfg['proxy.http']
        session.extra['interface.openaichat.enterpoint'] = enterpoint
