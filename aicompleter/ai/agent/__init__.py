'''
AI Agent
This module will enable you to create a AI agent to automaticly self-yield the message.
'''

from .agent import Agent
from .reagent import Agent as ReAgent
from .interface import AgentInterface, ReAgentInterface

__all__ = (
    'Agent',
    'AgentInterface',
    'ReAgent',
    'ReAgentInterface'
)
