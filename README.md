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

## Quick Start

The code below will start a talk with gpt, the detailed model varies with your configure, default is gpt-3.5-turbo.

```python
from aicompleter import *
from aicompleter.implements import *
import asyncio

cfg = Config({
    # 'openaichat' is the namespace, you can change to your own namespace
    'openaichat':{
        'openai':{
            'api-key': 'sk-...',                 # Put you OpenAI API key here
            'model': 'gpt-3.5-turbo',            # AI model, default is gpt-3.5-turbo
        }
    }
})
# ChatAI, use openai model gpt-3.5-turbo-0301
chater = ai.openai.Chater(cfg['openaichat'])
# Chat Interface, based on chater -> OpenAI API
chatinterface:ai.ChatInterface = ai.ChatInterface(ai=chater, namespace='openaichat')
# Handler, interacting between interfaces
hand:Handler = Handler(cfg)

async def main():
    # Add Interfaces
    await hand.add_interface(chatinterface)
    # Start a new session
    session:Session = await hand.new_session()
    print("Please start a conversation")
    while True:
        # Get input from console
        word = input(">>> ")
        if word == 'exit':
            break
        # Send a ask command to the chat interface, the ai is asked by the content (text, the question of user)
        print(await session.asend('ask', word))

# Start the loop
asyncio.run(main())
```

## Examples

See [examples](/examples/)

## Document

Reference: [Document](/doc/language.md)

## To-do List

We are adding more support to this program.
- [x] Add Commands Intergation with AI model.
  - [x] Add Commands Support
- [ ] Add memory system
  - [x] Add History
  - [ ] Add Memory Analyse
- [ ] Add Extra Interface Package
