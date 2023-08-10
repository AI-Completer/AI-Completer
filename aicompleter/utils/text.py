from typing import Any, Coroutine, Optional, Self
import trafilatura as tr
import aiohttp
import asyncio
import json
import re
from .. import common

def contains_substring(original, target):
    index = 0
    for char in original:
        if index >= len(target):
            return False
        if char == target[index]:
            index += 1
            if index == len(target):
                return True
    return False

class RemoteWebPage(common.AsyncContentManager):
    def __init__(self, url, proxy: Optional[str] = None, **options):
        self.url = url
        self.proxy = proxy
        self.options = options
        self._page_cache = None
        self._session = aiohttp.ClientSession()
        self._bs4_cache = None

    async def __aenter__(self) -> Self:
        await self._get_page()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._session.close()

    async def _get_page(self):
        if self._page_cache is None:
            async with self._session.get(self.url, proxy=self.proxy, **self.options) as response:
                response.raise_for_status()
                self._page_cache = await response.text()
        return self._page_cache

    async def getText(self) -> str:
        '''
        Get the main content from the web page
        '''
        return tr.extract(await self._get_page(), include_links=True).strip()

    async def getJson(self) -> dict:
        '''
        Get the main content in json format from the web page
        '''
        return json.loads(tr.extract(await self._get_page(), include_links=True, include_images=True, output_format='json'))

    async def getLines(self) -> list[str]:
        '''
        Get the main content from the web page, and split it into lines
        '''
        return (await self.getText()).splitlines()

    def __del__(self):
        if not self._session.closed:
            asyncio.create_task(self._session.close())

    async def getParsed(self):
        if self._bs4_cache is None:
            import bs4
            self._bs4_cache = bs4.BeautifulSoup(await self._get_page(), 'html.parser')
        return self._bs4_cache

def getWebText(url: str, *, proxy: Optional[str] = None) -> Coroutine[Any, Any, str]:
    '''
    Get the text from the web page
    '''
    return RemoteWebPage(url, proxy=proxy).getText()

def getChunkedText(text: str, split_length: int) -> list[str]:
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
                    raise Exception(
                        f"Cannot split the line {subline} into length {split_length}")
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

def getChunkedToken(token:list[int], limit_len:int) -> list[list[int]]:
    '''
    Split the token into limited length
    '''
    result = []
    cur = []
    for t in token:
        if len(cur) + 1 > limit_len:
            if len(t) > limit_len:
                raise Exception(
                    f"Cannot split the token {t} into length {limit_len}")
            result.append(cur)
            cur = [t]
            continue
        cur.append(t)
    if cur:
        if len(cur) > limit_len:
            raise Exception(
                f"Cannot split the token {cur} into length {limit_len}")
        result.append(cur)
    return result

async def getChunkedWebText(url: str, split_length: int, *, proxy: Optional[str] = None) -> list[str]:
    '''
    Get the text from the web page and split it into limited length
    '''
    return getChunkedText(await getWebText(url, proxy=proxy), split_length)

async def download(url: str, path: str, *, base_url: Optional[str] = None, **options) -> None:
    '''
    Download the file from the url
    '''
    async with aiohttp.ClientSession(base_url) as session:
        async with session.get(url, **options) as response:
            if response.status != 200:
                raise aiohttp.ClientError(
                    f"Cannot download file from {url} with status code {response.status}")
            with open(path, 'wb') as f:
                async for chunk in response.content.iter_any():
                    f.write(chunk)

def extract_text(html: str) -> str:
    '''
    Extract the main content from the html
    '''
    return tr.extract(html, include_links=True).strip()

def extract_html(html):
    '''
    Extract the main container from the html
    '''
    from bs4 import BeautifulSoup
    if isinstance(html, str):
        soup = BeautifulSoup(html, 'html.parser')
    elif isinstance(html, BeautifulSoup):
        soup = html
    else:
        raise TypeError(
            f"Cannot extract html from {html} with type {type(html)}")

    # tag: article
    articles = soup.find_all('article')
    if len(articles) == 1:
        return articles[0]
    elif len(articles) != 0:
        # Multi articles
        # find their common parent
        common_parent = None
        for article in articles:
            if common_parent is None:
                common_parent = article.parent
            else:
                while article.parent != common_parent:
                    article = article.parent
                    common_parent = common_parent.parent
        return common_parent
    
    # id: main
    main = soup.find(id='main')
    if main is not None:
        return main
    
    # id: post (keyword)
    post = [*soup.find_all(id='post'), *soup.find_all(class_='post')]
    if len(post) == 1:
        return post[0]
    elif len(post) != 0:
        # find the common parent
        common_parent = None
        for p in post:
            if common_parent is None:
                common_parent = p.parent
            else:
                while p.parent != common_parent:
                    p = p.parent
                    common_parent = common_parent.parent
        return common_parent
    
    # id: content (keyword)
    content = [*soup.find_all(id='content'), *soup.find_all(class_='content')]
    if len(content) == 1:
        return content[0]
    elif len(content) != 0:
        # find the common parent
        common_parent = None
        for c in content:
            if common_parent is None:
                common_parent = c.parent
            else:
                while c.parent != common_parent:
                    c = c.parent
                    common_parent = common_parent.parent
        return common_parent
    
    return None

def clear_html(html, restructure: bool = False):
    '''
    Clear the html
    '''
    import bs4
    from bs4 import BeautifulSoup
    if isinstance(html, str):
        soup = BeautifulSoup(html, 'html.parser')
    elif isinstance(html, BeautifulSoup):
        soup = html
    else:
        raise TypeError(
            f"Cannot clear html from {html} with type {type(html)}")
    
    # remove all comments
    for comment in soup.find_all(text=lambda text: isinstance(text, bs4.Comment)):
        comment.extract()
    # remove ' ','\n', ... outside of tag
    for element in soup.find_all(text=lambda text: isinstance(text, bs4.NavigableString)):
        element.replace_with(re.sub(r'\s+', ' ', element.string).strip())

    for element in soup.select('*'):
        if element.decomposed:
            continue
        # remove header, footer, script, noscript, style, link, aside, meta
        if element.name in ('header', 'footer', 'script', 'noscript', 'style', 'link', 'aside', 'meta'):
            element.decompose()
            continue
        # remove style attribute
        if element.attrs == None:
            element.attrs = {}
        id = element.get('id', '')
        classes = element.get('class', [])
        if element.has_attr('style'):
            del element['style']
        # remove data attribute
        for attr in list(element.attrs.keys()):
            if attr.startswith('data-'):
                del element[attr]
        # remove class 'nav'
        if any('nav' in c and 'has' not in c for c in classes) or \
            ('nav' in id and 'has' not in id):
            element.decompose()
            continue
        # remove comment
        if any('comment' in c and 'has' not in c for c in classes) or \
            ('comment' in id and 'has' not in id):
            element.decompose()
            continue
        # remove svg with link
        if element.name == 'img' and element.get('src', '').endswith('.svg') and element.parent.name == 'a':
            element.parent.decompose()
            continue
        # remove hidden element
        if element.name == 'input' and element.get('type', '') == 'hidden':
            element.decompose()
            continue
        if element.hidden:
            element.decompose()
            continue
        # remove empty link (no href,'#',javascript:void(0))
        if element.name == 'a' and element.get('href', '#') in ('#', 'javascript:void(0)'):
            element.decompose()
            continue
        # remove empty element (except br, a, img)
        if element.name not in ('br', 'a', 'img') and element.text.strip() == '' and len([i for i in element.children]) == 0:
            element.decompose()
            continue

    if restructure:
        # try to remove the nesting div
        def _unwrap():
            for element in soup.select('div'):
                if element.parent.name == 'div':
                    element.unwrap()
        for _ in range(4):
            _unwrap()

    return soup
