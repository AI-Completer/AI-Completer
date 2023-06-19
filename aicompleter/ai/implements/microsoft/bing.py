import enum
import time
import uuid
from typing import Any, Coroutine, Optional

from EdgeGPT import Chatbot, ConversationStyle

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
        self.update_config(config)

    def update_config(self, config:Config) -> None:
        self.proxy:Optional[str] = config.get('proxy', None)

    def new_history(self, user:Optional[str] = None, id:Optional[uuid.UUID] = None) -> Conversation:
        '''
        Create a new history
        '''
        return Conversation(user=user, id=id or uuid.uuid4(), time=time.time(), timeout=60*60*3, data={'num':0,'continue':True})
    
    async def ask(self, message: Message, history: Conversation, style:Style = Style.balanced, search_result:bool = True) -> Coroutine[Message, Any, None]:
        '''
        Ask the AI
        '''
        id = history.id
        self._bot_map.setdefault(id, Chatbot(proxy=self.proxy))
        bot = self._bot_map[id]

        if not history.data['continue']:
            del self._bot_map[id]
            raise error.AIGenerateError("Conversation Ended")
        
        async for ret in bot.ask_stream(message.content, style=style.value, search_result=search_result):
            ret_messages = ret['item']['messages']
            def __bot_messages():
                for i in ret_messages:
                    if i['author'] == 'bot' and 'text' in i:
                        yield i['text']
            messages = list(__bot_messages())
            yield ai.Message(content='\n\n'.join(messages), data=ret ,role='assistant')
