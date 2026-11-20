"""Polite public-source HTTP with per-host spacing and bounded retries."""
from time import monotonic, sleep
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "VietLeapInsightKit/1.0 (ratewatch)"


class PublicHttp:
    def __init__(self, client):
        self.client = client
        self.last = {}
        self.robots = {}

    def _get(self, url):
        host = urlsplit(url).netloc
        for attempt in range(3):
            sleep(max(0, self.last.get(host, 0) + 2 - monotonic()))
            self.last[host] = monotonic()
            try:
                response = self.client.get(url)
            except httpx.TransportError:
                if attempt == 2:
                    raise
            else:
                if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                    return response
            sleep(2 ** attempt)

    def __call__(self, url):
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.robots:
            response = self._get(origin + "/robots.txt")
            parser = RobotFileParser()
            if response.status_code not in (404, 410):
                response.raise_for_status()
                parser.parse(response.text.splitlines())
            else:
                parser.allow_all = True
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt không cho phép: {url}")
        response = self._get(url)
        response.raise_for_status()
        return response.content
