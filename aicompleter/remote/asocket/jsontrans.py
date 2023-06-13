import json
from typing import Optional
from .base import *

class jsonconnection(connection):
    '''
    JSON Connection
    '''
    def __init__(self, encode:str = 'utf-8'):
        super().__init__()
        self._code = encode

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

