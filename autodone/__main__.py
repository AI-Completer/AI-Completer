import os
import asyncio
from autodone import *
from autodone.config import Config
from autodone.utils import ainput,aprint
from . import log

__DEBUG__:bool = False
'''
For debug
'''
os.environ.setdefault('DEBUG', "False")
if os.environ['DEBUG'] == "True":
    __DEBUG__ = True

logger = log.Logger("Main")
formatter = log.Formatter()
handler = log.ConsoleHandler()
handler.formatter = formatter
logger.addHandler(handler)
if __DEBUG__:
    logger.setLevel(log.DEBUG)
else:
    logger.setLevel(log.INFO)

_handler:Handler = None
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
    openaichat_interface:Interface = implements.openai.OpenaichatInterface(User(
        name=name,
        in_group="agent",
        support={"text"},
    ))
    # Handler
    global _handler
    _handler = Handler(config)
    await _handler.add_interface(console_interface, initialier_interface, openaichat_interface)
    # Session
    session:Session = await _handler.new_session()
    # Start
    await session.start(console_interface, "ask", "Please Start your conversation with AI.", __DEBUG__)

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    loop.run_until_complete(main())
    loop.run_forever()
except KeyboardInterrupt:
    logger.info("KeyboardInterrupt")
    # loop.stop()
    # loop.run_until_complete(_handler.close())
    loop.stop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.run_forever()
    loop.stop()
    loop.close()
