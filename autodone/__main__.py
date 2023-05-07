import os
import asyncio
from autodone import *

async def main():
    # Console Interface
    console_interface:Interface = implements.ConsoleInterface(Character(
        name="Console",
        role=Role.USER,
        support_text=True,
        support_image=False,
        support_audio=False,
    ))
    # Initialier Interface
    initialier_interface:Interface = implements.InitInterface(Character(
        name="Initialier",
        role=Role.SYSTEM,
        support_text=False,
        support_image=False,
        support_audio=False,
    ))
    # To-do: Add a AI interface

    # Handler
    handler:Handler = Handler()
    handler.add_interface(console_interface)
    handler.add_interface(initialier_interface)
    # Session
    session:Session = handler.new_session()
    # Start
    # To-do: Add a command to start the session

loop = asyncio.new_event_loop()
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
loop.run_until_complete(main())
