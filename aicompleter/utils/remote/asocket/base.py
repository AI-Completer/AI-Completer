import asyncio
from typing import Any, Callable, Coroutine, Optional

class connection:
    '''
    asyncio connection wrapper
    '''
    def __init__(self):
        self._reader = None
        self._writer = None
        self._open = False

    async def connect(self, host:Optional[str] = None, port:Optional[int] = None, *args, **kwargs):
        '''
        Connect to a host and port
        '''
        if self._open:
            raise RuntimeError('Already connected')
        self._reader, self._writer = await asyncio.open_connection(host, port, *args, **kwargs)
        self._open = True

    async def send(self, data:bytes):
        '''
        Send data
        '''
        if not self._open:
            raise RuntimeError('Not connected')
        self._writer.write(data)
        await self._writer.drain()

    async def recv(self, size:int = 1024) -> bytes:
        '''
        Receive data
        '''
        if not self._open:
            raise RuntimeError('Not connected')
        return await self._reader.read(size)
    
    async def close(self):
        '''
        Close the connection
        '''
        if not self._open:
            raise RuntimeError('Not connected')
        self._writer.close()
        await self._writer.wait_closed()
        self._open = False

    def __del__(self):
        if self._open:
            self._writer.close()

class server:
    '''
    asyncio server wrapper
    '''
    def __init__(self):
        self._server = None
        self._open = False
        self._on_connect = None

    def set_on_connect(self, func:Callable[[connection], Coroutine[None, None, Any]]):
        '''
        Set the on_connect callback
        '''
        self._on_connect = func

    async def listen(self, host:Optional[str] = None, port:Optional[int] = None, *args, **kwargs):
        '''
        Listen to a host and port
        '''
        if self._open:
            raise RuntimeError('Already listening')
        async def connected(reader, writer):
            if self._on_connect:
                new_connection = connection()
                new_connection._reader = reader
                new_connection._writer = writer
                new_connection._open = True
                await self._on_connect(new_connection)
        self._server = await asyncio.start_server(connected,host, port,*args, **kwargs)
        self._open = True
        await self._server.start_serving()

    async def listen_forever(self, host:Optional[str] = None, port:Optional[int] = None, *args, **kwargs):
        '''
        Listen to a host and port forever
        '''
        if self._open:
            raise RuntimeError('Already listening')
        async def connected(reader, writer):
            if self._on_connect:
                new_connection = connection()
                new_connection._reader = reader
                new_connection._writer = writer
                new_connection._open = True
                await self._on_connect(new_connection)
        self._server = await asyncio.start_server(connected,host, port,*args, **kwargs)
        self._open = True
        await self._server.serve_forever()

    def close(self):
        '''
        Close the server
        '''
        if not self._open:
            raise RuntimeError('Not listening')
        self._server.close()
        self._open = False

    async def wait_closed(self):
        '''
        Wait for the server to close
        '''
        if not self._open:
            raise RuntimeError('Not listening')
        await self._server.wait_closed()
        self._open = False

    @property
    def is_open(self) -> bool:
        '''
        Check if the server is open
        '''
        return self._open
    
    def __del__(self):
        if self._open:
            self._server.close()

            