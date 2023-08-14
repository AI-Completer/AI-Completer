from typing import Optional
import uuid

from ...ai.implements.openai.api import Chater
from ...ai import ChatInterface, AI
from ... import *

class SummaryInterface(ChatInterface):
    cmdreg:Commands = Commands()

    def __init__(self, ai:AI, config:Config = Config(), id: uuid.UUID = uuid.uuid4()):
        super().__init__(
            ai=ai,
            namespace='summary',
            user = User(
                description='summary interface user, can summarize a text',
                in_group='ai',
                support={'text'},
            ),
            config=config,
            id=id,
        )
        
    async def summarize(self, text: str, user:Optional[str] = None, language:str = 'en-us') -> str:
        '''
        Summarize a short text
        Unsupported for long text whose tokens is greater than the model limit
        '''
        self.ai:Chater
        base_conversation = self.ai.new_conversation(user=user,init_prompt=\
f'''
You are ChatGPT, an AI that can summarize a text.
Your task is to summarize the text.
If you think the text cannot be summarized, you can just return 'None'.

Here is the text:
```text
{text}
```
'''
        )    
        from ... import language as lg
        ret = await self.ai.ask_once(base_conversation, ai.Message(
            content = lg.DICT[language]['start_task'],
            role = 'user',
        ))

        if ret == 'None':
            return text
        else:
            return ret

    @cmdreg.register('summary', 'Summarize a text', format={'text': 'The text to summarize'})
    async def cmd_summary(self, session: Session, message: Message):
        '''
        Summarize a text
        '''
        text = message.content.json['text']
        ret = await self.summarize(text, user=session.id.hex[0:8])
        return ret
