from __future__ import annotations
import aiohttp
from autodone.interface.base import Character
import autodone.session as session
import attr
import json
import logging
import uuid
import time
import asyncio
from autodone.interface import Role

class Content(object):
    '''Common content class.'''

class Text(Content,str):
    '''Text content.'''

class Image(Content):
    '''Image content.'''
    def __init__(self, url:str) -> None:
        self.url = url

    def __str__(self) -> str:
        return f"![{self.url}]({self.url})"
    
    def __repr__(self) -> str:
        return f"Image({self.url})"

class Audio(Content):
    '''Audio content.'''
    def __init__(self, url:str) -> None:
        self.url = url

    def __str__(self) -> str:
        return f"![{self.url}]({self.url})"
    
    def __repr__(self) -> str:
        return f"Audio({self.url})"

class MultiContent(Content):
    '''Combine text, images and audios.'''
    def __init__(self) -> None:
        self.contents:list[Content] = []

    def add(self, content:Content) -> None:
        '''Add a content.'''
        self.contents.append(content)
    
    def remove(self, content:Content) -> None:
        '''Remove a content.'''
        self.contents.remove(content)

    @property
    def text(self) -> str:
        '''Get text content.'''
        return "".join([str(content) for content in self.contents])

    @property
    def pure_text(self) -> str:
        '''Get pure text content.'''
        return "".join([str(content) for content in self.contents if isinstance(content, Text)])
    
    @property
    def images(self) -> list[Image]:
        '''Get image content.'''
        return [content for content in self.contents if isinstance(content, Image)]
    
    @property
    def audios(self) -> list[Audio]:
        '''Get audio content.'''
        return [content for content in self.contents if isinstance(content, Audio)]

class Session:
    '''Session'''
    LOGGER=logging.getLogger(__name__)
    def __init__(self) -> None:
        self.create_time: float = time.time()
        '''Create time'''
        self.last_used: float = self.create_time
        '''Last used time'''
        self.history:list[Message] = []
        '''History'''
        self.lock: asyncio.Lock = asyncio.Lock()
        '''Lock'''
        self._closed: bool = False
        '''Closed'''
        self.roles:list[Role] = []
        '''Role list'''
        self.active_role:Role|None = None
        '''Active role'''
        self.id:uuid.UUID = uuid.uuid4()
        '''ID'''
        self.extra:dict = {
            'http_session':aiohttp.ClientSession(),
        }
        '''Extra information'''

    async def acquire(self) -> None:
        await self.lock.acquire()
        self.last_used = time.time()
    
    def release(self) -> None:
        self.lock.release()
    
    @property
    def locked(self) -> bool:
        return self.lock.locked()
    
    def __getitem__(self):
        return self.extra.__getitem__()
    
    def __setitem__(self):
        return self.extra.__setitem__()
    
    def __delitem__(self):
        return self.extra.__delitem__()
    
    def __contains__(self):
        return self.extra.__contains__()
    
    def __iter__(self):
        return self.extra.__iter__()
    
    def __len__(self):
        return self.extra.__len__()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.http_session.close()
    
    @property
    def closed(self) -> bool:
        return self._closed

class Message:
    '''A normal message from the Interface.'''
    def __init__(self, character:Character, content:MultiContent, session:Session,cmd:str = "ask",id:uuid.UUID = uuid.uuid4(), from_:Message|None = None) -> None:
        self.character:Character = character
        '''Character of the message'''
        self.content:MultiContent = content
        '''Content of the message'''
        self.session:Session = session
        '''Session of the message'''
        self.id:uuid.UUID = id
        '''ID of the message'''
        self.extra:dict = {}
        '''Extra information'''
        self.last_message:Message|None = from_
        '''Last message'''
        self.cmd:str = cmd
        '''Call which command to transfer this Message'''
        

    def __str__(self) -> str:
        return f"{self.character.name}: {self.content.text}"
    
    def __repr__(self) -> str:
        return f"Message({self.character.name}, {self.content.text}, {self.session.id}, {self.id})"
    
