import os
import asyncio
from autodone import *

async def main():
    # Console Interface
    console_interface:Interface = implements.ConsoleInterface()
    # Initialier Interface
    initialier_interface:Interface = implements.InitInterface()
    # To-do: Add a AI interface

    # Handler
    handler:Handler = Handler()
    handler.add_interface(console_interface)
    handler.add_interface(initialier_interface)
    await handler.init_interfaces()
    # Session
    session:Session = handler.new_session()
    # Start
    # To-do: Add a command to start the session

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
loop.run_until_complete(main())
