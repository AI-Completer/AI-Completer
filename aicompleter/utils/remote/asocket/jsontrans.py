from __future__ import annotations
import json
from typing import Optional
from .base import *
from asyncio import Lock

class jsonconnection(connection):
    '''
    JSON Connection
    '''
    def __init__(self, encode:str = 'utf-8'):
        super().__init__()
        self._code = encode
        self._lock = Lock()

    class __conversation:
        def __init__(self, jc:jsonconnection):
            self._jc = jc

        async def __aenter__(self):
            await self._jc._lock.acquire()
            return self._jc
        
        async def __aexit__(self, exc_type, exc, tb):
            self._jc._lock.release()

    async def conversation(self):
        '''
        Get a conversation
        '''
        return self.__conversation(self)

    async def send(self, data:dict) -> None:
        '''
        Send data
        '''
        if not self._open:
            raise RuntimeError('Connection not open')
        self._writer.write(json.dumps(data).encode(self._code) + b'\n')
        await self._writer.drain()

    async def recv(self) -> dict:
        '''
        Receive data
        '''
        if not self._open:
            raise RuntimeError('Connection not open')
        content = await self._reader.readline()
        while content == b'\n':
            content = await self._reader.readline()
        return json.loads(content, encoding=self._code)
    
    @property
    def on_requesting(self) -> bool:
        '''
        Whether the connection is requesting
        '''
        return not self._lock.locked()
    
    async def wait_for_request(self) -> None:
        '''
        Wait for the connection to stop requesting
        '''
        await self._lock.acquire()
        self._lock.release()
    
    async def request(self, data:dict) -> dict:
        '''
        Send data and receive data
        '''
        async with self._lock:
            await self.send(data)
            return await self.recv()
        
    def at_eof(self) -> bool:
        '''
        Whether the connection is at eof
        '''
        return self._reader.at_eof()

class jsonserver(server):
    '''
    JSON Server
    '''
    def __init__(self, encode:str = 'utf-8'):
        super().__init__()
        self._code = encode

    async def listen(self, host:Optional[str] = None, port:Optional[int] = None, *args, **kwargs):
        '''
        Listen to a host and port
        '''
        if self._open:
            raise RuntimeError('Already listening')
        async def connected(reader, writer):
            if self._on_connect:
                await self._on_connect(jsonconnection(reader, writer, self._code))
        self._server = await asyncio.start_server(connected, host, port, *args, **kwargs)
        self._open = True
        await self._server.start_serving()

    async def listen_forever(self, host: str | None = None, port: int | None = None, *args, **kwargs):
        '''
        Listen forever
        '''
        if self._open:
            raise RuntimeError('Already listening')
        async def connected(reader, writer):
            if self._on_connect:
                await self._on_connect(jsonconnection(reader, writer, self._code))
        self._server = await asyncio.start_server(connected, host, port, *args, **kwargs)
        self._open = True
        await self._server.serve_forever()

