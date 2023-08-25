import asyncio
import sys, os
from typing import Coroutine, Literal, Optional, Union
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
import aicompleter as ac
from aicompleter import Config, Session, User
from aicompleter.ai import ChatTransformer

class WebExplorerConfigModel(ac.ConfigModel):
    '''
    Configuration model for web explorer
    '''
    driver: Literal['Chrome', 'Firefox', 'Edge', 'Safari', 'Ie'] = 'Chrome'
    '''
    The driver to use
    '''

driverFactory:dict[str, type[RemoteWebDriver]] = {
    'Chrome': webdriver.Chrome,
    'Firefox': webdriver.Firefox,
    'Edge': webdriver.Edge,
    'Safari': webdriver.Safari,
    'Ie': webdriver.Ie,
}

def getFullHtml(url:str, driver:str|RemoteWebDriver = 'Chrome') -> str:
    '''
    Get the full html of a web page
    '''
    if isinstance(driver, str):
        driver = driverFactory[driver]()
    driver.get(url)
    driver.implicitly_wait(10)
    ret = driver.find_element(By.CSS_SELECTOR, 'html').get_attribute('outerHTML')
    driver.quit()
    return ret

async def agetFullHtml(url:str, driver:str|RemoteWebDriver = 'Chrome') -> Coroutine[None, None, str]:
    '''
    Get the full html of a web page
    '''
    if isinstance(driver, str):
        driver = await ac.utils.thread_run(driverFactory[driver])()
    await ac.utils.thread_run(driver.get)(url)
    await ac.utils.thread_run(driver.implicitly_wait)(10)
    ret = await ac.utils.thread_run(driver.find_element)(By.CSS_SELECTOR, 'html')
    ret = await ac.utils.thread_run(ret.get_attribute)('outerHTML')
    await ac.utils.thread_run(driver.quit)()
    return ret

class WebExplorerDataModel(ac.DataModel):
    '''
    Data model for web explorer
    '''
    driver: Optional[RemoteWebDriver] = None
    '''
    The driver to use
    '''

class WebExplorerInterface(ac.Interface):
    '''
    The interface for web explorer
    '''
    cmdreg: ac.Commands = ac.Commands()
    configFactory = WebExplorerConfigModel
    dataFactory = WebExplorerDataModel

    def __init__(self, config: ac.Config = ac.Config()):
        super().__init__(
            'webexplorer',
            ac.User('webexplorer', 'Web Explorer, which can help you to explore the web page'),
            config = config,
        )
        
    async def session_init(self, session: ac.Session, config:WebExplorerConfigModel, data:WebExplorerDataModel):
        '''
        Session init
        '''
        if config['driver'] in driverFactory:
            data.driver = driverFactory[config['driver']]()
        else:
            raise ValueError(f"Invalid driver: {config['driver']!r}")
        
    async def session_close(self, session: ac.Session, config:WebExplorerConfigModel, data:WebExplorerDataModel):
        '''
        Session close
        '''
        data.driver.quit()

    @cmdreg.register('webopen', 'Open a web page, this will enable the web explorer', format={'url': 'The url to open'})
    async def webopen(self, data:WebExplorerDataModel, url:str):
        '''
        Open a web page
        '''
        data.driver.get(url)
        # Wait for page load
        await ac.utils.thread_run(data.driver.implicitly_wait)(10)

    @cmdreg.register('webtext', 'Get the text of a web element', format=ac.CommandParamStruct({
        'selector': ac.CommandParamElement('selector', str, 'body', 'The selector of the element', optional=True),
    }))
    async def webtext(self, data:WebExplorerDataModel, selector:str='*'):
        '''
        Get the text of a web element
        '''
        element = data.driver.find_element(By.CSS_SELECTOR, selector)
        if element is None:
            raise ValueError(f'Element not found: {selector}')
        return element.text

class WebSummarier(ac.ai.ChatInterface):
    '''
    Web summarier
    
    Used to summarize a web page,
    this class is different from webanalyse module,
    this class will use selenium to get the web page content,
    '''
    cmdreg: ac.Commands = ac.Commands()
    configFactory = WebExplorerConfigModel

    def __init__(self, ai: ChatTransformer, config: Config = Config(), id: uuid.UUID = uuid.uuid4()):
        super().__init__(ai=ai, namespace="websummary", user=User(
            name = 'description',
            description = 'Web Summarier, which can help you to summarize a web page',
            in_group='ai',
        ), id=id, config=config)

    async def session_init(self, session: Session):
        '''
        Session init
        '''
        session.in_handler.require_interface(ac.implements.logical.SummaryInterface)

    @cmdreg.register('websummarize', 'Summarize a web page', format={'url': 'The url to summarize'})
    async def websummarize(self, session:ac.Session, config: WebExplorerConfigModel, url:str):
        '''
        Summarize a web page
        '''
        driver = None
        try:
            driver = driverFactory[config.driver]()
        except KeyError:
            raise ValueError(f"Invalid driver: {config.driver}")
        with driver:
            driver.get(url)
            # Wait for page load
            await ac.utils.thread_run(driver.implicitly_wait)(10)
            # Get the text
            text = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerText')
            encoded = self.ai.getToken(text)
            if len(encoded) <= 1024:
                # There is no need to summarize a short text
                return text
            # Try extract the main content
            text = ac.utils.extract_text(driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML'))
            encoded = self.ai.getToken(text)
            split_token = ac.utils.getChunkedToken(encoded, 2048)
            # Summarize the text
            # Get the summary class
            summary_interface = session.in_handler.require_interface(ac.implements.logical.SummaryInterface)
            # Get the summary
            sem = asyncio.Semaphore(5)
            async def summary(token:list[int]):
                async with sem:
                    return await session.send(
                        "summary", {'text': self.ai.encoder.decode(token)},
                        src_interface=self,
                        dest_interface=summary_interface,
                    )
            summaries = await asyncio.gather(*[summary(token) for token in split_token])
            return '\n'.join(summaries)

    @cmdreg.register("webimage", "Get the images of a web page", format={'url': 'The url to get the images'})
    async def webimage(self, config: WebExplorerConfigModel, url:str):
        '''
        Get the images of a web page
        '''
        driver = None
        try:
            driver = driverFactory[config['driver']]()
        except KeyError:
            raise ValueError(f"Invalid driver: {config['driver']!r}")
        with driver:
            driver.get(url)
            # Wait for page load
            await ac.utils.thread_run(driver.implicitly_wait)(10)
            # Get the html
            html = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML')
            import bs4
            html = ac.utils.clear_html(html, True)
            main_container = ac.utils.extract_html(html)
            if main_container == None:
                main_container = html
            # Get the images
            images:bs4.ResultSet[bs4.Tag] = main_container.find_all('img')
            return [{
                'src': image.get('src', 'undefined'),
                'alt': image.get('alt', 'undefined'),
            } for image in images]
