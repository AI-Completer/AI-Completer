import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import aicompleter as ac

# Set global log level
ac.log.setLevel(ac.log.WARNING)

# Set Config, you can also load it from file
config = ac.Config({
    "global":{
        "openai":{
            "api-key":"<Input your api key here>",
            # OpenAI API key (Required)
            # You can get it from https://platform.openai.com/account/api-keys
        },
    },
    'openaichat':{
        'model': 'gpt-3.5-turbo',
        # Model(Optional, default: gpt-3.5-turbo)
        # See the model list in https://platform.openai.com/docs/models/overview
        # Note: You can only use specialized models if you use chat interface
    }
})
config.update_global()

# Load the handler, where all the interfaces are stored and interacted
handler = ac.Handler(config=config)

# Load AI (OpenAI GPT for chat)
ai = ac.ai.openai.Chater(config=config['openaichat'])
# Setup the AI to the interface
ai_int = ac.ai.ChatInterface(ai=ai, namespace='openaichat')

async def main():
    # Setup handler
    await handler.add_interface(ai_int)
    # Open a new session
    session = await handler.new_session()

    # Start conversation
    while True:
        # Get input
        # Alternatively, you can use the ConsoleInterface (`ac.implemets.ConsoleInterface`) to get input
        # but for this example, it's not necessary
        try:
            text = input('>>> ')
        except (KeyboardInterrupt, EOFError):
            break
        if text == 'exit':
            break
        print("Response: ", await session.asend(
            'ask',text
        ))

ac.utils.start(main())
