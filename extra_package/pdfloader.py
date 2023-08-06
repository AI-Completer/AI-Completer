from __future__ import annotations
import sys
import os
import uuid
from typing import Optional

import pdfplumber

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from aicompleter import Config, Session, User
from aicompleter.ai import ChatTransformer
from aicompleter.config import Config
from aicompleter.interface import User
from aicompleter.utils.endict import EnhancedDict

import aicompleter as ac

class PDFloader(ac.ai.ChatInterface):
    '''
    PDF loader
    You can ask to load PDF and for some questions about loaded PDF
    '''
    cmdreg = ac.Commands()

    def __init__(self, *, ai: ChatTransformer, id: uuid.UUID | None = None, config: Config = Config()):
        super().__init__(
            ai=ai,
            namespace='pdfloader',
            user= User(
                name='PDFloader',
                description='PDF loader',
                in_group='ai',
                support={'pdf'},
            ),
            config=config,
            id=id or uuid.uuid4(),
        )

    def load(self, filepath:str, chunk_size:int = 512):
        '''
        Load PDF
        '''
        file = pdfplumber.open(filepath)
        text = ''
        for page in file.pages:
            text += page.extract_text()
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        return chunks
    
    async def session_init(self, session: Session, data: EnhancedDict):
        # await super().session_init(session)
        # not call super().session_init() because it is not necessary

        # Construct memory
        from aicompleter.memory import faissimp as fimpl
        memory = fimpl.FaissMemory()
        data['memory'] = memory
        data['pdfloaded'] = False
    
    @cmdreg.register('load-pdf', 'Load PDF file, enable PDF-related commands', format={'path':'The path of PDF file'})
    async def cmd_load(self, session:ac.Session, message:ac.Message, data:EnhancedDict):
        '''
        Load PDF
        '''
        if data['pdfloaded']:
            raise ac.error.Existed('PDF already loaded')
        data['pdfloaded'] = True

        filepath = message['path']
        chunks = self.load(filepath)
        from aicompleter.memory import faissimp as fimpl
        memory: fimpl.FaissMemory = data['memory']
        memory.put([ac.memory.MemoryItem(content=value, ) for index, value in enumerate(chunks)])
        self.logger.debug(f'PDF loaded: {filepath}')
        return

    @cmdreg.register('query', 'Query PDF content, get relative text', format={'query':'Query string'})
    async def cmd_query(self, session:ac.Session, message:ac.Message, data:EnhancedDict):
        '''
        Query PDF
        '''
        if not data['pdfloaded']:
            raise ac.error.NotFound('PDF not loaded')
        from aicompleter.memory import faissimp as fimpl
        memory: fimpl.FaissMemory = data['memory']
        query = message['query']
        result = memory.query(ac.memory.Query(query, 3))
        # Return result in string
        return '\n\n'.join(i.value for i in result)
    