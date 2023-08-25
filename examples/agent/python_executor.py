'''
This is a simple example of how to use the executor interface.
This will enable the agent to execute python code.
'''

import sys
import os

sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))

import aicompleter as ac
# Set global log level to DEBUG
# This is sometimes important because GPT may continously generate wrong commands
ac.log.setLevel(ac.log.DEBUG)

config = ac.Config({
    "global": {
        "openai": {
            "api-key": "<Input your api key here>",
            # OpenAI API key (Required)
            # You can get it from https://platform.openai.com/account/api-keys
        },
    },
    "openaichat": {},
})
config.update_global()

# Load the handler
handler = ac.Handler(config=config)
# Load AI (OpenAI GPT for chat)
ai = ac.ai.openai.Chater(config=config['openaichat'])

# Setup the AI to Executor Interface
# This interface will load an agent to interact with the user
agent_int = ac.implements.logical.SelfStateExecutor(
    ai=ai, namespace='openaichat')

# Console interface
# This interface will get input from console
# This interface contain a command named 'ask' which will enable the AI to ask the user
console_int = ac.implements.ConsoleInterface()
# Commands : ask, echo

# Python Code Interface
python_int = ac.implements.PythonCodeInterface()
# Commands : exec

# Author Interface
# This interface will check the authority of all commands
# Ask for permission if the authority is not enough
author_int = ac.implements.AuthorInterface()
# Provide no commands


async def main():
    # Add graph to control privilege
    grpah = ac.layer.InterfaceDiGraph()
    # Enable agent to call the commands of ConsoleInterface (ask, echo)
    grpah.add(agent_int, console_int)
    grpah.add(console_int, python_int)
    
    grpah.add(author_int, console_int)  # Authority Interface require console command

    await grpah.setup(handler)

    # Open a new session
    session = await handler.new_session()

    # Start conversation
    # In this example, you can ask the agent: What commands can you execute?
    init_word = await session.asend(ac.Message(
        cmd='ask',
        content={'content': 'Please start a conversation'},
        dest_interface=console_int,
    ))
    # Start agent
    await session.asend(ac.Message(
        cmd='agent',
        content=init_word,
        dest_interface=agent_int,
    ))

ac.utils.start(main())
