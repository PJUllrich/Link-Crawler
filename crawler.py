import asyncio
import re
from typing import Iterator
from urllib.parse import ParseResult, urlparse

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL


class Crawler:
    """
    Inspiration: https://github.com/aosabook/500lines/blob/master/crawler
    /code/crawling.py
    """
    MAX_WORKERS = 5

    def __init__(self, root: str):
        # asyncio stuff
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.workers = []

        self.visited = set([root])
        self.q = asyncio.Queue(loop=self.loop)
        self.q.put_nowait((root, root))

        netloc_raw = urlparse(root).netloc
        self.netloc = netloc_raw.replace('www.', '')
        self.count_scan, self.count_added = 1, 1

    def start(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._setup())
        except KeyboardInterrupt:
            print('Crawler stopping...')
            loop.run_until_complete(self._close())
        finally:
            # Next 2 lines are needed for aiohttp resource cleanup
            loop.stop()
            loop.run_forever()

            loop.close()

    async def _setup(self):
        print('Setting up workers...')
        self.workers = [asyncio.Task(self._work(), loop=self.loop)
                        for _ in range(self.MAX_WORKERS)]
        print('Starting scan...')
        await self.q.join()
        await self._close()

    async def _work(self):
        try:
            while True:
                url, parent = await self.q.get()
                await self._scan(url, parent)
                self.q.task_done()
        except asyncio.CancelledError:
            print(f'Worker stopped!')

    async def _scan(self, url: str, parent: str):
        try:
            res = await self.session.get(url)

            self.count_scan += 1
            print(f'\r{self.count_scan} of {self.count_added} '
                  f'({(self.count_scan / self.count_added):.2f}%) '
                  f'links scanned. ',
                  end='')
        except aiohttp.ClientError as e:
            print(f'Error! {parent} - {url} - {e}')
            return

        if res.status >= 400:
            print(f'Broken! {parent} - {url} - {res.status}')
            return

        for link in await self._find_links(res):
            if link not in self.visited:
                self.count_added += 1
                self.visited.add(link)
                self.q.put_nowait((link, url))

    async def _find_links(self, res: aiohttp.ClientResponse) -> Iterator[str]:
        content = await res.text()
        soup = BeautifulSoup(content, 'html.parser')
        links = [self._format(res.url, a) for a in soup.find_all('a')]
        return filter(lambda l: l is not None, links)

    def _format(self, parent: URL, tag: {}):
        url = tag.get('href', None)
        if url is None:
            return None

        parsed = urlparse(url)
        if parsed.netloc == '':
            parsed = parsed._replace(scheme=parent.scheme)
            parsed = parsed._replace(netloc=parent.host)

        return parsed.geturl() if self._is_valid(parsed) else None

    def _is_valid(self, url: ParseResult):
        if (
                re.match('(.*).' + self.netloc, url.netloc) is None or
                re.match('(.*)\+[0-9]*$', url.path) is not None or
                re.match('(.*)javascript:(.*)', url.path) is not None
        ):
            return False

        return True

    async def _close(self):
        for w in self.workers:
            w.cancel()

        await self.session.close()
