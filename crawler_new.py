import re
from collections import deque
from typing import Iterator
from urllib.parse import urljoin, urlparse

import progress
import requests
from bs4 import BeautifulSoup
from progress.counter import Counter
from requests import RequestException, Response


class Crawler:
    root: str
    netloc: str
    counter: progress.counter.Counter

    def __init__(self, root: str):
        self.root = root
        self.counter = Counter()
        netloc_raw = urlparse(root).netloc
        self.netloc = netloc_raw.replace('www.', '')

    def start(self):
        visited = set([self.root])
        q = deque([(self.root, self.root)])

        while q:
            url, parent = q.popleft()
            try:
                res = requests.get(url)
            except RequestException as e:
                print(f'Error: {e} on {url}')
                continue

            if res.status_code != requests.codes.ok:
                print(f'Parent: {parent} - '
                      f'Link: {url} '
                      f'State: {res.status_code}')
                continue

            for link in self._find_links(res):
                if link not in visited:
                    visited.add(link)
                    q.append((link, url))

                    self.counter.index += 1
                    self.counter.update()

    def _find_links(self, res: Response) -> Iterator[str]:
        soup = BeautifulSoup(
            res.content,
            'html.parser',
            from_encoding="iso-8859-1"
        )
        links = [self._format(res.url, a) for a in soup.find_all('a')]
        return filter(lambda l: l is not None, links)

    def _format(self, url, tag: {}):
        link = tag.get('href', None)
        if link is None:
            return None

        parsed = urlparse(link)
        if parsed.netloc == '':
            parent = urlparse(url)
            netloc = parent.scheme + '://' + parent.netloc
        else:
            netloc = parsed.scheme + '://' + parsed.netloc

        if re.match('(.*).' + self.netloc, netloc) is None:
            return None

        return urljoin(netloc, parsed.path)
