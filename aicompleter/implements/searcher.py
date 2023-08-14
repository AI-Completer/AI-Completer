'''
Search Interface
'''
import uuid
from typing import Optional
from aicompleter import Session
from aicompleter.interface.base import User
from .. import *

class SearchInterface(ai.ChatInterface):
    '''
    Search Interface
    '''
    def __init__(self, config:Config, id: uuid.UUID = uuid.uuid4()):
        super().__init__(
            ai = ai.implements.microsoft.BingAI(config),
            user = User(
                name = 'searcher',
                in_group='ai',
                all_groups={'ai', 'searcher'},
                support={'text'}
            ),
            namespace = 'searcher',
            id = id,
        )
        self.commands.add(Command(
            cmd = 'search',
            description = 'Search on the web by Bing AI',
            format=CommandParamStruct({
                'query': CommandParamElement('query', str, description='Search query')
            }),
            callback = self.cmd_search,
            in_interface=self,
        ))

    async def session_init(self, session: Session):
        self.getdata(session)['conversation'] = self.ai.new_conversation(session.id.hex[:8])

    async def cmd_search(self, session: Session, message: Message):
        '''
        Search
        '''
        data = self.getdata(session)
        conversation = data['conversation']
        query = message.content.json['query']
        if not query:
            raise ValueError('Query cannot be empty')
        return await self.ai.ask_once(conversation, ai.Message(
            content = query,
            role = 'user',
            user = session.id.hex[:8],
        ))
