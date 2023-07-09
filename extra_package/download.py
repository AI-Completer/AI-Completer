import os
import sys
import asyncio
import aiohttp

import aicompleter.session as session
from aicompleter.implements.system.file import FileSystem, WorkSpace

sys.path.append('..')

from aicompleter import *

class DownloadInterface(Interface):
    '''
    Download interface
    '''
    def __init__(self, config:Config = Config()):
        super().__init__(
            user=User(
                name='download',
                description='Download Interface',
                in_group='system',
            ),
            namespace='download',
            config=config,
        )
        self.commands.add(Command(
            cmd='download',
            description='Download a file(Sync)',
            expose=True,
            in_interface=self,
            to_return=True,
            force_await=True,
            callback=self.cmd_download,
            format=CommandParamStruct({
                'path':CommandParamElement(name='path', type=str, required=True, description='The path of the file'),
                'url':CommandParamElement(name='url', type=str, required=True, description='The url of the file'),
            }),
        ))
        
    async def session_init(self, session: Session) -> None:
        data = self.getdata(session)
        data['session'] = aiohttp.ClientSession()

        if not session.in_handler.has_interface(implements.system.FileInterface):
            raise error.NotFound('FileInterface is required')

        return await super().session_init(session)

    async def session_final(self, session: Session) -> None:
        data = self.getdata(session)
        await data['session'].close()
        return await super().session_final(session)

    async def cmd_download(self, session: Session, message: Message) -> None:
        '''
        Download a file
        '''
        gdata = session.data['global']
        ws:WorkSpace = gdata['workspace']

        data = self.getdata(session)
        path:str = message.content['path']
        url:str = message.content['url']
        # Check permission
        f = ws.get(path, message.src_interface.user)
        if f == None:
            raise error.PermissionDenied('Permission denied when opening the file', interface=self)
        try:
            with f.open('wb') as file:
                async with data['session'].get(url) as resp:
                    resp: aiohttp.ClientResponse
                    if resp.status != 200:
                        raise error.BaseException(f"Download failed, status={resp.status}")
                    async for i in resp.content:
                        file.write(i)
        except BaseException as e:
            # Check Exception
            ws.remove(path)
            raise e
        return 'success'
