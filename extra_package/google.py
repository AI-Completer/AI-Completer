import os
import sys
import uuid
from typing import Optional

import bs4

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from urllib import parse

import aiohttp

import aicompleter as ac
from aicompleter.config import Config
from aicompleter.interface.command import (CommandParamElement,
                                           CommandParamStruct)


class GoogleInterface(ac.Interface):
    '''
    Google interface
    '''
    def __init__(self, config:Config = Config(), id:uuid.UUID = uuid.uuid4(), user:Optional[ac.User] = None):
        super().__init__(
            namespace='google',
            config=config,
            id=id,
            user=user or ac.User(
                description='google interface user, can search through the web search engine',
                in_group='system',
                support={'text'},
            )
        )
        self.commands.add(ac.Command(
            cmd='google',
            description='google search, get links and titles',
            in_interface=self,
            callback=self.cmd_google,
            to_return=True,
            force_await=True,
            format=CommandParamStruct({
                'query': CommandParamElement(name='query', type=str, description='search query'),
            })
        ))

    async def yield_google(self, query:str,*, top_n:int = 10, proxy:Optional[str] = None,user_agent:Optional[str] = None, session:Optional[aiohttp.ClientSession] = None):
        '''
        google search

        Note: if possible, please use Google API instead of this method
        '''
        query = parse.quote(query)
        # Get the search result
        async def _request():
            nonlocal session
            if session is None:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'https://www.google.com/search?q={query}&num={top_n}',
                        proxy=proxy,
                        headers={
                            'User-Agent': user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
                        }) as resp:
                        html = await resp.text()
            else:
                async with session.get(
                    f'https://www.google.com/search?q={query}&num={top_n}',
                    proxy=proxy,
                    headers={
                        'User-Agent': user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
                    }) as resp:
                    html = await resp.text()

            # Parse the html
            soup = bs4.BeautifulSoup(html, 'html.parser')
            ret = soup.find_all('div', class_='g')
            if len(ret) == 0:
                if 'This page appears when Google automatically detects requests coming from your computer network which appear to be in violation of the' in html:
                    raise ac.error.Failed('google search failed, authorization needed')
                else:
                    raise ac.error.NotFound('there is no result')
            return ret
        
        results = await _request()

        # Parse the results
        index = 0
        while index + 1 < len(results):
            result = results[index]
            index += 1

            title = result.find('h3').text
            
            # Get the link
            anchors = result.find_all('a')
            if len(anchors) == 0:
                continue
            link = anchors[0]['href']
            if link.startswith('/url?q='):
                link = link[7:]
            if not link.startswith('http'):
                continue
            if link.find('&sa=U&') != -1:
                link = link[:link.find('&sa=U&')]

            # brief = result.find('span', class_='st').text
            yield {
                'title': title,
                'link': link,
                # 'brief': brief,
            }

    async def google(self, query:str,*, top_n:int = 10, proxy:Optional[str] = None,user_agent:Optional[str] = None, session:Optional[aiohttp.ClientSession] = None):
        '''
        google search

        Note: if possible, please use Google API instead of this method
        '''
        results = []
        async for result in self.yield_google(query, top_n=top_n, proxy=proxy, user_agent=user_agent, session=session):
            results.append(result)
        return results
    
    async def session_init(self, session: ac.Session) -> None:
        ret = await super().session_init(session)
        self.getdata(session)['session'] = aiohttp.ClientSession()
        return ret
    
    def cmd_google(self, session:ac.Session, message: ac.Message):
        '''
        Interface Command Google, search and get links
        '''
        data = self.getdata(session)
        config = self.getconfig(session)
        query = message['query']
        return self.google(query, 
                           top_n=10,
                           proxy=config.get('proxy', None),
                           user_agent=config.get('user_agent', None),
                           session=data['session'],
                           )
    
    async def session_final(self, session: ac.Session) -> None:
        ret = await super().session_final(session)
        data = self.getdata(session)
        await data['session'].close()
        del data['session']
        return ret

if __name__ == '__main__':
    import asyncio
    async def main():
        google = GoogleInterface()
        results = await google.google('AI-Completer', top_n=20, proxy="http://127.0.0.1:10809")
        print(results)
    asyncio.run(main())
