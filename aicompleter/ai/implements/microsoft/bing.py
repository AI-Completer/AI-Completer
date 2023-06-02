import enum
import time
import uuid
from typing import Any, Coroutine, Optional

from EdgeGPT import Chatbot, ConversationStyle

from aicompleter import *
from aicompleter.ai import Conversation


@enum.unique
class Style(enum.Enum):
    'The style of conversation'
    balanced=ConversationStyle.balanced
    'Balanced'
    creative=ConversationStyle.creative
    'Creative'
    precise=ConversationStyle.precise
    'Precise'

class BingAI(ai.ChatTransformer):
    '''
    Microsoft Bing AI
    '''
    def __init__(self, config:Config) -> None:
        super().__init__()
        self._bot_map:dict[uuid.UUID, Chatbot] = {}
        self._record_map:dict[uuid.UUID, Conversation] = {}
        self.proxy:Optional[str] = config.get('proxy', None)
    
    async def ask(self, message: ai.Message, id:uuid.UUID = uuid.uuid4(), style:Style = Style.balanced, search_result:bool = True) -> Coroutine[ai.Message, Any, None]:
        '''
        Ask the AI
        '''
        self._bot_map.setdefault(id, Chatbot(proxy=self.proxy))
        bot = self._bot_map[id]
        self._record_map.setdefault(id, Conversation(timeout=60*60*3,data={'user_message':0}))
        
        async for ret in bot.ask_stream(message.content, style=style.value, search_result=search_result):
            ret_messages = ret['item']['messages']
            def __bot_messages():
                for i in ret_messages:
                    if i['author'] == 'bot' and 'text' in i:
                        yield i['text']
            messages = list(__bot_messages())
            yield ai.Message(content=messages[0] if len(messages) == 0 else messages[-1], data=ret,role='assistant')
