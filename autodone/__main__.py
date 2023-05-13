import os
import asyncio
from autodone import *
from autodone.config import Config
from autodone.utils import ainput,aprint
from . import log

global __DEBUG__
__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

logger = log.Logger("Main")

async def main():
    # Read Config
    if not os.path.exists("config.json"):
        config = Config()
    else:
        config = Config.loadFromFile("config.json")
    config.setdefault("global.debug", False)
    if config["global.debug"]:
        __DEBUG__ = True
        os.environ['DEBUG'] = "True"
    # Console Interface
    console_interface:Interface = implements.ConsoleInterface()
    # Initialier Interface
    initialier_interface:Interface = implements.InitInterface()
    # Input AI name
    if __DEBUG__:
        name = "Debug"
    else:
        name = await ainput("AI Name: ")
    # OpenAI Chat Interface
    openaichat_interface:Interface = implements.openai.OpenaichatInterface(Character(
        name=name,
        role=Role.AGENT,
    ))
    # Handler
    handler:Handler = Handler(config)
    await handler.add_interface(console_interface, initialier_interface, openaichat_interface)
    # Session
    session:Session = await handler.new_session()
    # Start
    await session.start(console_interface, "ask", "Please Start your conversation with AI.", __DEBUG__)

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
loop.run_until_complete(main())
loop.run_forever()
