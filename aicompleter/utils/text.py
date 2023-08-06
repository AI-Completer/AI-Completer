from typing import Any, Coroutine, Optional, Self
import trafilatura as tr
import aiohttp
import asyncio
from .. import common

class RemoteWebPage(common.AsyncContentManager):
    def __init__(self, url, proxy:Optional[str] = None, **options):
        self.url = url
        self.proxy = proxy
        self.options = options
        self._page_cache = None
        self._session = aiohttp.ClientSession()

    async def __aenter__(self) -> Self:
        await self._get_page()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._session.close()

    async def _get_page(self):
        if self._page_cache is None:
            async with self._session.get(self.url, proxy=self.proxy, **self.options) as response:
                if response.status // 100 != 2:
                    raise Exception(f"Error: {response.status}")
                self._page_cache = await response.text()
        return self._page_cache
    
    async def getText(self) -> str:
        return tr.extract(await self._get_page(), include_links=True).strip()
    
    async def getLines(self) -> list[str]:
        return (await self.getText()).splitlines()
    
    def __del__(self):
        if not self._session.closed:
            asyncio.create_task(self._session.close())

    async def getParsed(self):
        import bs4
        return bs4.BeautifulSoup(await self._get_page(), 'html.parser')
    
def getWebText(url:str, *, proxy:Optional[str] = None) -> Coroutine[Any, Any, str]:
    '''
    Get the text from the web page
    '''
    return RemoteWebPage(url, proxy=proxy).getText()

def getChunkedText(text:str, split_length:int) -> list[str]:
    '''
    Split the text into limited length
    '''
    lines = text.splitlines()
    result = []
    cur = ''

    def subsplit(line):
        # Try to split the line
        nonlocal cur, result
        from ..language import ALL_SPILTTER
        sublines = []
        subspliters = []
        subcur = ''
        # Split by sentence splitter
        for char in line:
            if char in ALL_SPILTTER:
                sublines.append(subcur)
                subcur = ''
            else:
                subcur += char
                subspliters.append(char)
        if subcur:
            sublines.append(subcur)
        # Split by length
        for subline in sublines:
            if len(cur) + len(subline) > split_length:
                if len(subline) > split_length:
                    raise Exception(f"Cannot split the line {subline} into length {split_length}")
                result.append(cur + subspliters.pop())
                cur = subline
                continue
            cur += subline
            subspliters.pop()

    for line in lines:
        if len(cur) + len(line) > split_length:
            if len(line) > split_length:
                subsplit(line)
                continue
            result.append(cur)
            cur = ''
        cur += line
    if cur:
        if len(cur) > split_length:
            subsplit(cur)
        else:
            result.append(cur)
    return result

async def getChunkedWebText(url:str, split_length:int, * ,proxy:Optional[str] = None) -> list[str]:
    '''
    Get the text from the web page and split it into limited length
    '''
    return getChunkedText(await getWebText(url, proxy=proxy), split_length)
