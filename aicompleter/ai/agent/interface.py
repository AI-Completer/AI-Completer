from abc import abstractclassmethod
import copy
import uuid
from typing import Optional

from aicompleter import Session, session
from aicompleter.common import serialize

from ...config import Config
from ...interface import User
from ...ai import TransformerInterface, ChatTransformer
from .. import ai
from ... import utils
from .agent import Agent

class AgentDataModel(utils.DataModel):
    '''
    The data model for agent
    '''
    agent: Agent

class AgentInterface(TransformerInterface):
    '''
    The interface for agent
    '''
    dataFactory = AgentDataModel

    def __init__(self, *, ai: ChatTransformer, namespace:str, user:Optional[User] = None, id: Optional[uuid.UUID] = None, config:Config=Config(), init_messages:Optional[list[ai.Message] | str] = None):
        super().__init__(ai=ai,namespace=namespace, user=user, id=id, config=config)
        self.ai.config.update(config)
        utils.typecheck(self.ai, ChatTransformer)

        self.init_messages = init_messages or []
        if isinstance(init_messages, str):
            from .. import ai as ai_
            self.init_messages = [ai_.Message(content=init_messages, role='system')]
        
    async def session_init(self, session: Session):
        agent = Agent(self.ai, user=session.id.hex[:8])
        self.ai: ChatTransformer
        conversation = self.ai.new_conversation(user=session.id.hex[:8])
        conversation.messages = copy.copy(self.init_messages)
        agent.conversation = conversation
        self.getdata(session)['agent'] = agent
    
    async def set_conversation(self, data:AgentDataModel, conversation:ai.Conversation):
        data.agent.conversation = conversation

    def __hash__(self):
        return hash(self.id)
    
    def getStorage(self, session: Session) -> dict | None:
        '''
        Get the storage of the agent
        '''
        return serialize(self.getdata(session)['agent'].conversation)
    
    @abstractclassmethod
    def setStorage(self, session: Session, data: dict):
        '''
        Set the storage of the agent
        '''
        raise NotImplementedError('This method is required to be implemented by subclass')
    
