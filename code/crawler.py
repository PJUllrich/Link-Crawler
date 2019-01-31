import asyncio
import re
from typing import Iterator
from urllib.parse import ParseResult, urlparse

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from reporter import Reporter


class Crawler:
    """
    A web crawler that checks the HTTP status of all links on a website and
    its sub-pages.

    The crawler uses the Breadth First Search algorithm to crawl a given
    website and all its subsidiaries. Websites that are out of scope (don't
    have the same network location as the give website) are ignored.

    Inspiration: https://github.com/aosabook/500lines/blob/master/crawler
    /code/crawling.py
    """
    MAX_WORKERS = 10

    def __init__(self, root: str):
        # asyncio stuff
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.workers = []

        self.visited = set([root])
        self.q = asyncio.Queue(loop=self.loop)
        self.q.put_nowait((root, root))

        self.netloc = urlparse(root).netloc.replace('www.', '')
        self.scanned = 0

    def start(self):
        """Starts the crawling. Cleans up after crawler is interrupted."""

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._setup())
        except KeyboardInterrupt:
            Reporter.info('Crawler stopping...')
        finally:
            loop.run_until_complete(self._close())

            # Next 2 lines are needed for aiohttp resource cleanup
            loop.stop()
            loop.run_forever()

            loop.close()

    async def _setup(self):
        """Starts the async workers. Runs until the task queue is empty."""

        Reporter.info('Setting up workers...')
        self.workers = [asyncio.Task(self._work(), loop=self.loop)
                        for _ in range(self.MAX_WORKERS)]
        Reporter.info('Starting scan...')
        await self.q.join()

    async def _work(self):
        """Pulls URLs from the task queue and scans them."""

        try:
            while True:
                url, parent = await self.q.get()
                await self._scan(url, parent)
                self.q.task_done()

                self.scanned += 1
                Reporter.status(self.scanned, self.q.qsize())
        except asyncio.CancelledError:
            Reporter.info('Worker stopped!')

    async def _scan(self, url: str, parent: str):
        """
        Fetches a URL HTML text and adds all links in the text to the
        task queue. If URL is not available, reports it.
        """

        Reporter.scan(parent, url)
        try:
            res = await self.session.get(url)
        except aiohttp.ClientError as e:
            Reporter.error(parent, url, e)
            return

        if res.status >= 400:
            Reporter.broken(parent, url, res.status)
            return

        for link in await self._find_links(res):
            if link not in self.visited:
                self.visited.add(link)
                self.q.put_nowait((link, url))

    async def _find_links(self, res: aiohttp.ClientResponse) -> Iterator[str]:
        """Finds all 'a' tags on the page. Parses and returns them."""

        content = await res.text()
        soup = BeautifulSoup(content, 'html.parser')
        links = [self._format(res.url, a) for a in soup.find_all('a')]
        return filter(lambda l: l is not None, links)

    def _format(self, parent: URL, tag: {}):
        """
        Retrieves, formats, and returns URLs from an 'a' tag.
        Returns None, if no URL was found or if URL does is not valid.
        """

        url = tag.get('href', None)
        if url is None:
            return None

        parsed = urlparse(url)
        if parsed.netloc == '':
            parsed = parsed._replace(scheme=parent.scheme)
            parsed = parsed._replace(netloc=parent.host)

        return parsed.geturl() if self._is_valid(parsed) else None

    def _is_valid(self, url: ParseResult):
        """Checks if a URL complies with a given set of validators."""

        if (
                re.match('(.*).' + self.netloc, url.netloc) is None or
                re.match('(.*)\+[0-9]*$', url.path) is not None or
                re.match('(.*)javascript:(.*)', url.path) is not None
        ):
            return False

        return True

    async def _close(self):
        """Cancels all workers. Closes aiohttp session."""
        for w in self.workers:
            w.cancel()

        await self.session.close()
