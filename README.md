# AI-Completer

A totally automatic AI to interact with environments.

Now it only supports OpenAI API.

## Setup

*Note*:Please use stable branch if the dev branch is broken

1. Clone the Repositry

```shell
git clone https://github.com/AI-Completer/AI-Completer.git
cd AI-Completer
```

2. Modify the config file

You can use either vim or your editor to modify the file `config-example.json`, and save it to `config.json`

3. Run and enjoy yourself

*Note*: Use Python 3.11+ to run this program.

```shell
python3 -m aicompleter talk --ai bingai
# This will start a conversation with bing ai.
python3 -m aicompleter helper --enable-agent --include pythoncode
# This will start a helper with OpenAI API
```

You can add custom interface to this program to add more function.

## Usage

```python
from aicompleter import *
from aicompleter.implements import *
import asyncio

cfg = config.loadConfig('config.json')
# load config
cfg['openaichat'].setdefault(cfg['global'])
# load global config to overwrite openaichat config
chater = ai.openai.Chater(cfg['openaichat'])
# ChatAI, use openai model gpt-3.5-turbo-0301
consoleinterface:ConsoleInterface = ConsoleInterface()
# Console Interface
chatinterface:ai.ChatInterface = ai.ChatInterface(ai=chater, namespace='openaichat')
# Chat Interface, based on chater -> OpenAI API
hand:Handler = Handler(cfg)
# Handler, interacting between interfaces

async def main():
    await hand.add_interface(consoleinterface, chatinterface)
    # Add Interfaces to the handler, you can also use aicompleter.layer module to manage rights
    session:Session = await hand.new_session()
    # Start a new session
    ret = None
    while True:
        text = await session.asend(Message(
            cmd='ask',
            session=session,
            dest_interface=consoleinterface,
            content=ret if ret else "Start Your Conversation",
        )) # Send a ask command to the console interface, the console will print the message and require user to input
        ret = await session.asend(Message(
            cmd='ask',
            session=session,
            dest_interface=chatinterface,
            content=text,
        )) # Send a ask command to the chat interface, the ai is asked by the content (text, the question of user)

        # continue to execute

asyncio.run(main())
# Start the loop

```

## Document

Reference: [Document](doc/language.md)

## To-do List

We are adding more support to this program.
- [x] Add Commands Intergation with AI model.
  - [x] Add Commands Support
- [ ] Add memory system
  - [x] Add History
  - [ ] Add Memory Analyse
- [ ] Add More Extra Interface
- [ ] Add GUI support
