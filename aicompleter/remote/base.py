import json
import uuid
from aicompleter import *
from .asocket import jsonserver, jsonconnection

__standard__ = r'''
json interface interaction standard:
when the connection is established, the server will send a dict: {namespace: str}
base structure: {type: str}
    bothend commands:
        add-command: 
            {type: 'add-command', data: Command.__to_json__()}
            return nothing
        remove-command:
            {type: 'remove-command', name: str}
            return nothing
        execute:
            {type: 'execute', cmd: str, content: MultiContent, interface: str, uuid: str, async: bool, last_message: str}
            return: {type: 'success', result: str, raw_type: str}
    for server:
    for client:
        close:
            {type: 'close'}
            return nothing
'''

# TODO: Add command callback, for client

class RemoteInterface(Interface):
    '''
    Remote Interface
    Will start a connection to a remote server,
    transmit the data, and return the result,
    It will use the remote Interface to do the work
    '''

    @property
    def namespace(self) -> str:
        if self._namespace:
            return self._namespace
        raise RuntimeError('Connection not established')
    
    def __init__(self, host:str = 'localhost', port:int = 8080, *, ssl = None) -> None:
        self.host = host
        self.port = port
        self._ssl = ssl
        self._namespace = None
        self._connect = jsonconnection()
        self._history_sessions:dict[uuid.UUID,Session] = {}
        # To call command from remote without session parameter

    async def _common_callback(self, session:Session, message:Message):
        '''
        Common callback for command
        '''
        await self._connect.send({'type': 'execute', 'session': session.id, message: message.__to_json__()})

    async def _recv_execute(self, data:dict):
        '''
        Analyze the data and execute the command
        '''
        match data['type']:
            case 'add-command':
                new_command = Command.__from_json__(data['data'])
                new_command.callback = self._common_callback
                self.commands.add(new_command)
            case 'remove-command':
                self.commands.remove(data['name'])
            case 'execute':
                session = self._history_sessions.get(uuid.UUID(data['uuid']), None)
                if session == None:
                    await self._connect.send({'type': 'error', 'error': 'Session not found'})
                    return
                try:
                    last_message = None
                    if 'last_message' in data:
                        for message in session.history:
                            if message.id == data['last_message']:
                                last_message = message
                                break
                        if last_message == None:
                            await self._connect.send({'type': 'error', 'error': 'Last Message not found'})
                            return
                    if data.get('async', False):
                        session.send(Message(
                            content = MultiContent(data['content']),
                            cmd = data['cmd'],
                            src_interface = self,
                            dest_interface = session.in_handler.get_interface(data['interface'], False),
                            last_message = last_message,
                        ))
                        await self._connect.send({'type': 'success'})
                    else:
                        result = await session.asend(Message(
                            content = MultiContent(data['content']),
                            cmd = data['cmd'],
                            src_interface = self,
                            dest_interface = session.in_handler.get_interface(data['interface'], False),
                            last_message = last_message,
                        ))
                        raw_type = result.__class__.__name__
                        if hasattr(result, '__to_json__'):
                            result = json.dumps(result.__to_json__())
                        elif isinstance(result, dict):
                            result = json.dumps(result)
                        else:
                            result = str(result)
                        await self._connect.send({'type': 'success', 'result': result, 'raw_type': raw_type})
                except Exception as e:
                    await self._connect.send({'type': 'error', 'error': str(e)})
            case _:
                await self._connect.send({'type': 'error', 'error': 'Unknown type'})
    
    async def init(self) -> None:
        '''
        Initialize the interface
        '''
        await super().init()
        await self._connect.connect(self.host, self.port, ssl = self._ssl)
        try:
            data = await self._connect.recv()
            self._namespace = data['namespace']
        except Exception as e:
            await self._connect.close()
            raise RuntimeError('The data received is not valid') from e

    async def final(self) -> None:
        '''
        Finalize the interface
        '''
        await super().final()
        await self._connect.send({'type': 'close'})
        await self._connect.close()
