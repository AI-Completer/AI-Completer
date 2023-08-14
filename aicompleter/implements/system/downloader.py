import contextlib
import uuid
from typing import Optional
import aiohttp

from ... import *
from .file import FileInterface

class Downloader(Interface):
    cmdreg:Commands = Commands()

    def __init__(self, config: Config = Config(), id: uuid.UUID = uuid.uuid4()):
        super().__init__(
            "downloader",
            User(
                description="Web downloader, download web page/resource and save it to local file.",
                in_group='system',
                support={'web'},
            ),
            id=id,
            config=config,
        )
    
    async def session_init(self, session: Session | None = None):
        session.in_handler.require_interface(FileInterface, self.user)

    @cmdreg.register("download", "Download web page/resource and save it to local file.", format={'url': 'str', 'path': 'str'})
    async def download(self, session: Session, message:Message, url: str, path: str):
        """Download web page/resource and save it to local file."""
        file_int:FileInterface = session.in_handler.require_interface(FileInterface, self.user)
        ws = file_int.getworkspace(session)

        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(url) as resp:
                    resp.raise_for_status()
                    with ws.get(path).open('w', user=message.src_interface.user) as f:
                        async for data in resp.content.iter_any():
                            f.write(data)

        except Exception as e:
            with contextlib.suppress(error.NotFound):
                ws.remove(path, user=message.src_interface.user)
            raise e
