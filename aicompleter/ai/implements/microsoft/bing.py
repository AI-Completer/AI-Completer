import enum
import time
import uuid
from typing import Any, Coroutine, Optional

from EdgeGPT.EdgeGPT import Chatbot, ConversationStyle

from aicompleter import *
from aicompleter.ai import Conversation, ChatTransformer, Message

@enum.unique
class Style(enum.Enum):
    'The style of conversation'
    balanced=ConversationStyle.balanced
    'Balanced'
    creative=ConversationStyle.creative
    'Creative'
    precise=ConversationStyle.precise
    'Precise'

class BingAI(ChatTransformer):
    '''
    Microsoft Bing AI
    '''
    def __init__(self, config:config.Config) -> None:
        super().__init__()
        self._bot_map:dict[uuid.UUID, Chatbot] = {}
        self._last_message_map:dict[uuid.UUID, dict] = {}
        self.update_config(config)

    def update_config(self, config:config.Config) -> None:
        self.proxy:Optional[str] = config.get('proxy', None)

    def new_conversation(self, user:Optional[str] = None, id:Optional[uuid.UUID] = None) -> Conversation:
        '''
        Create a new history
        '''
        return Conversation(user=user, id=id or uuid.uuid4(), time=time.time(), timeout=60*60*3, data={'num':0,'continue':True})
    
    async def ask(self, message: Message, history: Conversation, style:Style = Style.balanced, search_result:bool = True) -> Coroutine[str, Any, None]:
        '''
        Ask the AI
        '''
        id = history.id
        if id not in self._bot_map:
            self._bot_map[id] = await Chatbot.create(proxy=self.proxy)
        bot = self._bot_map[id]

        if not history.data['continue']:
            del self._bot_map[id]
            del self._last_message_map[id]
            raise error.AIGenerateError("Conversation Ended")
        
        last_message = ''
        async for final, ret in bot.ask_stream(message.content, conversation_style=style.value, search_result=search_result):
            if not final:
                yield ret
                last_message = ret
            else:
                yield last_message
                self._last_message_map[id] = ret
        
