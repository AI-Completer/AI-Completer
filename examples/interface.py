import sys, os
from typing import Coroutine
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import aicompleter as ac

ac.log.setLevel(ac.log.DEBUG)

class CustomInterface(ac.Interface):
    '''
    Make a custom interface
    '''
    cmdreg = ac.Commands() # Commands Register, you can add custom command easily by this

    def __init__(self, config: ac.Config = ac.Config(), id:uuid.UUID = uuid.uuid4()):
        # __init__ method should contain config parameter
        super().__init__(
            namespace = 'custom',               # Namespace of the interface, every Interface should have a unique namespace

            user=ac.User(                       # User of the interface
                                                # Most of time, it just plays a role of permission control
                                                # And information display. As a result, the user can be optional in most cases

                name = 'custom-user',           # User name
                description= 'Custom user',
                in_group = 'system',            # User main group
                support = {'text'}              # User support
            )
        )

    @cmdreg.register('customcmd', 'Just a custom command')
    async def cmd_customcmd(self, session: ac.Session, message: ac.Message):
        # Do something
        self.logger.info("Here, the custom command is called, name: customcmd")
        self.logger.info("The message is: %s" % message.content)
        return None # You can return a value 
    
    @cmdreg.register('customcmd2', 'Another command',
                    format={'param1':'value1'})
    # This command requires a parameter named 'param1' with value description 'value1'
    # There is a format check on this command, if not satisfied, the command will not be executed and a exception will be raised
    # The command can be non-async, the result will be collected and returned as a coroutine
    def cmd_customcmd2(self, message: ac.Message, data: ac.EnhancedDict, config: ac.Config):
        # command can have two optional parameters
        # data: session data on this interface, can be get by 'self.getdata(session)'
        # config: session config on this interface (including this), can be get by 'self.getconfig(session)'
        self.logger.info("Here, the custom command is called, name: customcmd2")
        self.logger.info("The message is: %s" % message.content)
        self.logger.info("The param1 is: %s" % message['param1'])
        self.logger.info("The data is: %s" % data)
        return "values"
    
    async def init(self, in_handler: ac.Handler) -> Coroutine[None, None, None]:
        # in_handler is optional
        # This will be called when the interface is added to the handler
        await super().init(in_handler)

    async def final(self) -> Coroutine[None, None, None]:
        # This will be called when the interface is removed from the handler,
        # or when the handler is closed
        await super().final()

    async def session_init(self, session: ac.Session):
        # This is called when a session is created, you can have some operations on the new created session
        await super().session_init(session)

    async def session_final(self, session: ac.Session):
        # When a session is closed, the method would be called
        await super().session_final(session)

@CustomInterface.cmdreg.register('custom3', '...')
async def cmd_customcmd3(message: ac.Message, interface: CustomInterface):
    # You can also register a command outside the interface
    interface.logger.info("Here, the custom command is called, name: customcmd3")
    interface.logger.info("The message is: %s" % message.content)
    return None

custom_int = CustomInterface()
handler = ac.Handler()

async def main():
    await handler.add_interface(custom_int)
    session = await handler.new_session()
    await session.asend(ac.Message('customcmd', 'Hello world!'))
    await session.asend(ac.Message('customcmd2', {'param1':'Hello world!'}))
    await session.asend(ac.Message('custom3', 'Hello world!'))

# A simple way to start the coroutine with runtime check
ac.utils.start(main())
