import asyncio
import copy
import uuid
from abc import abstractclassmethod
from typing import Optional

from ... import Session, utils
from ...ai.ai import AuthorType, ChatTransformer, Conversation, Message as AIMessage
from ...ai.interface import TransformerInterface
from ...common import serialize
from ...config import Config
from ...interface import Command, CommandCall, Interface, User
from ...session import Message
from ...utils import DataModel
from .. import ai
from .agent import Agent
from .reagent import Agent as ReAgent
from ... import Handler, error

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
    

class ReAgentDataModel(DataModel):
    '''
    ReChat Data Model
    '''
    agent:ReAgent

    init_conversation: Conversation

class ReAgentInterface(TransformerInterface):
    '''
    New chat interface due to the refactoring of agent
    '''
    dataFactory = ReAgentDataModel
    def __init__(self, ai: ChatTransformer, namespace:Optional[str] = None, user:Optional[User] = None, id:Optional[uuid.UUID] = None, config:Config = Config(),* ,loop:Optional[asyncio.AbstractEventLoop] = None):
        super().__init__(ai=ai, namespace=namespace, user=user, id=id, config=config)
        self._loop = loop
        self.inform_ope = CommandCall('ask', {"content":"{content}"})
        if self.__class__ == ReAgentInterface:
            @self.commands.register('agent', 'Start an agent', callable_groups={'user', 'system'},in_interface=self)
            def agent(session:Session, message:Message, data:ReAgentDataModel):
                if data.agent.closed:
                    # Start another agent
                    data.agent = ReAgent(self.ai, data.init_conversation)
                @data.agent.on_response
                async def _on_response(agent: ReAgent, msg: AIMessage):
                    def slim_exception(e: Exception):
                        # remove __cause__
                        if e.__cause__:
                            e.__cause__ = None
                        newargs = []
                        for i in e.args:
                            if isinstance(i, (Message, Interface, Session, Command)):
                                pass
                            elif isinstance(i, Exception):
                                newargs.append(slim_exception(i))
                            else:
                                newargs.append(i)
                        e.args = newargs
                        if isinstance(e, error.BaseException):
                            # have kwargs
                            newkwargs = {}
                            for k,v in e.kwargs.items():
                                if isinstance(i, (Message, Interface, Session, Command)):
                                    pass
                                elif isinstance(i, Exception):
                                    newkwargs[k] = slim_exception(v)
                                else:
                                    newkwargs[k] = v
                            e.kwargs = newkwargs
                        return e
                    
                    try:
                        ope, value = msg.content.split(':', 1)
                    except:
                        agent.append_message(AIMessage('parse error, reply or use a command?', role=AuthorType.SYSTEM))
                        return
                    value = value.strip()
                    match ope.strip():
                        case 'reply':
                            # reply
                            try:
                                ret = await self.inform_ope.template(content=value.strip()).call(session, src_interface=self)
                            except Exception as e:
                                # Inform command should not raise any error
                                self.logger.critical("Inform command should not raise any error, exiting")
                                raise e
                            else:
                                agent.append_word(ret)
                                return
                        case 'command':
                            # command
                            try:
                                cmd, argfull = value.split(',', 1)
                            except:
                                self.logger.error("Command Parse Failed")
                                agent.append_message(AIMessage('Command parse failed', role=AuthorType.SYSTEM))
                                return
                            # parse argfull
                            cmd = cmd.strip()
                            argfull = argfull.strip()
                            if not argfull.startswith("args:"):
                                # format error
                                self.logger.error("Command Parse Failed")
                                agent.append_message(AIMessage('Command parse failed', role=AuthorType.SYSTEM))
                            else:
                                arg = argfull[5:].strip()

                            async def _stop(arg):
                                agent.set_result(arg)
                                agent.close()
                            special_commands = {'stop':_stop}
                            if cmd in special_commands:
                                special_commands[cmd](arg)
                                return

                            try:
                                ret = await session.asend(cmd, arg, src_interface=self)
                            except Exception as e:
                                agent.append_message(AIMessage('failed: %s' % (slim_exception(e),), role=AuthorType.SYSTEM))
                                return
                            agent.append_message(AIMessage('result: %s' % (ret,)))
                        case _:
                            # unknown
                            agent.append_message(AIMessage('parse error, unknown operation: %s' % (ope, ), role=AuthorType.SYSTEM))
                            return

                data.agent.append_word(message.content.pure_text)

    async def session_init(self, session:Session, data:ReAgentDataModel):
        commands = list(session.in_handler.get_executable_cmds(self.user))
        commands.append(Command('stop', 'Stop the conversation with a message'))
        command_info = '\n'.join([
            f'{index} {cmd.name}: {cmd.description}, args: {cmd.format.json_text if cmd.format else "any"}'
            for index, cmd in enumerate(commands, 1)
        ])
        init_conversation: Conversation = Conversation(
            [AIMessage(\
f'''\
You are PaLM, a chatbot that help user to solve the problem.

Commands:
{command_info}

Note:
1. You can't use the nonexisted command.
2. You can't connect to the network in this session.
3. If you need to reply to the user, use "reply:" prefix, if you want to execute a command, use "command:" prefix.
4. Your reply will be parsed as markdown.

Examples:
user: Hello.<|END|>
you: reply: Hello, how can I help you?<|END|>
user: Try to google "ABC"<|END|>
you: command: google, args: {{"query":"ABC"}}<|END|>

Here start the true conversation:
''')])
        data.agent = ReAgent(self.ai, init_conversation)
        data.init_conversation = init_conversation

    def set_conversation(self, session:Session, conversation:Conversation):
        agent:ReAgent = session.data['agent']
        agent.conversation = conversation
    