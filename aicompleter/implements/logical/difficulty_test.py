from aicompleter import *
from aicompleter.ai import ChatInterface, ChatTransformer, Conversation
from aicompleter.config import Config
from typing import (
    Optional,
    TypeVar,
)

import uuid
import json

class DifficultyTestInt(ChatInterface):
    '''
    The AI Interface to mark the difficulty of the task
    '''
    def __init__(self, *, ai: ChatTransformer,user:Optional[str] = None, id: Optional[uuid.UUID] = None, config:Config= Config()):
        super().__init__(ai=ai, namespace='diff-test', user=user, id=id, config=config)
        self.commands.add(
            Command(
                cmd='mark-difficulty',
                description='Mark the difficulty of the task',
                expose=True,
                in_interface=self,
                to_return=True,
                force_await=True,
                callback=self.cmd_mark,
            )
        )

    async def cmd_mark(self, session: Session, message:Message):
        '''
        Mark the difficulty of the task
        '''
        ret = await self.ai.generate_text(
            conversation=Conversation(
                messages=[
                    ai.Message(
                        content='''
You are a marking bot.
Your task is to mark the difficulty of the task for AI, who have limited tokens and memory but access to computer and Internet. It can operate the computer only through terminal.
You need to reply with the json format below(important!):
{
    "overall": <int>,
    "logic": <int>,
    "comprehension": <int>,
    "calculation": <int>,
    "code": <int>,
    "memory": <int>
}
The integers are from 1 to 10, 1 means the easiest, 10 means the hardest.
What the user said is the task.
If what user said is not a task, no matter what the content is, reply with "Not task". (important!)
If what user said miss many details, reply with "Missing details". (important!)
Do not reply with anything else.
                        ''',role='system'
                    ),
                    ai.Message(
                        content=message.content.text,
                        role='user',
                    )
                ]
            )
        )

        if ret.startswith('Not task'):
            raise error.AI_InvalidTask(content=ret, interface=self, message=message)
        
        if ret.startswith('Missing details'):
            raise error.AI_RequireMoreDetail(content=ret, interface=self, message=message)
        
        try:
            ret = json.loads(ret)
        except json.JSONDecodeError:
            raise error.AI_InvalidJSON(content=ret, interface=self, message=message)
        
        if not isinstance(ret, dict):
            raise error.AI_InvalidJSON(content=ret, interface=self, message=message, detail = 'Not a dict')
        
        if set(ret.keys()) != {'overall', 'logic', 'comprehension', 'calculation'}:
            raise error.AI_InvalidJSON(content=ret, interface=self, message=message, detail = 'Not a valid dict')
        
        return ret
