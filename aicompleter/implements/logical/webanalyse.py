import asyncio
import uuid
from typing import Any, Coroutine, Optional
from ... import *

class WebAnalyse(Interface):
    '''
    Web Analyse
    Will Analyse the web page and return the result
    '''
    def __init__(self, *, user: Optional[str] = None, id: Optional[uuid.UUID] = None, config: Config = Config()):
        super().__init__(
            namespace='webanalyse', 
            user=User(
                name = user or '',
                description='web analyse interface user, can analyse a web page',
                in_group='ai',
                support={'text'},
            ), 
            id=id or uuid.uuid4(), 
            config=config
        )
        self.commands.add(Command(
            cmd='web-analyse',
            description='Analyse a web page, get the summary',
            format = CommandParamStruct({
                'url': CommandParamElement('url', str, description='The url of the web page', tooltip='url'),
                'request': CommandParamElement('request', str, description='The extra request about the text', tooltip='request', optional=True, default=''),
            }),
            callback=self.cmd_analyse,
        ))

    async def init(self, in_handler: Handler) -> None:
        # Check summary interface
        from .summarizer import SummaryInterface
        if not in_handler.has_interface(SummaryInterface):
            raise Exception('WebAnalyse interface requires SummaryInterface')

    async def analyse(self, session:Session, url: str, user: Optional[str] = None, language: str = 'en-us', split_length:int = 3072, *, proxy:Optional[str] = None) -> str:
        '''
        Analyse a web page
        '''
        from ...utils import text
        from .summarizer import SummaryInterface

        lines = await text.getChunkedWebText(url, split_length=split_length, proxy=proxy)
        summary_interface:SummaryInterface = session.in_handler.get_interface(SummaryInterface)[0]
        if len(lines) == 1 and len(summary_interface.ai.getToken(lines[0])) < 1024:
            return lines[0]
        
        sem = asyncio.Semaphore(5)
        async def _get_summary(line):
            async with sem:
                self.logger.debug(f'Getting summary for {line}')
                return await summary_interface.summarize(line, user=user, language=language)
        
        # Summary
        summaries = await asyncio.gather(*(_get_summary(line) for line in lines))
        return '\n\n'.join(summaries)

    def cmd_analyse(self,session:Session, message:Message) -> Coroutine[Any, Any, str]:
        '''
        Analyse a web page
        '''
        url = message.content.json['url']
        config = self.getconfig(session)
        return self.analyse(
            session, 
            url, 
            user=session.id.hex[0:8], 
            language=config.get('language', 'en-us'),
            proxy=config.get('proxy', None)
            )
    
