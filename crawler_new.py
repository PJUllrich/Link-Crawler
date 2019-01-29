from collections import deque
from typing import List, Iterator
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class Crawler:
    root: str
    netloc: str

    def __init__(self, root: str):
        self.root = root
        self.netloc = urlparse(root).netloc

    def start(self):
        broken = {}
        visited = set([self.root])
        q = deque([self.root])

        while q:
            url = q.popleft()
            res = requests.get(url)

            if res.status_code != requests.codes.ok:
                broken[url] = res.status_code
                print(f'Broken: {url}, States: {res.status_code}')
                continue

            for link in self._find_links(res.content):
                if link not in visited and self._within_netloc(link):
                    print(link)
                    visited.add(link)
                    q.append(link)

    def _find_links(self, page: bytes) -> Iterator[str]:
        soup = BeautifulSoup(page, 'html.parser')
        links = [self._fix_link(a) for a in soup.find_all('a')]
        return filter(lambda l: l is not None, links)

    def _fix_link(self, tag: {}):
        link = tag.get('href', None)

        if link is None:
            return None

        parsed = urlparse(link)
        if parsed.netloc == '':
            link = urljoin(self.root, link)

        return link

    def _within_netloc(self, link: str):
        return urlparse(link).netloc == self.netloc
