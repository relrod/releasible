import re

class GitHubAPICall:
    def __init__(self, token, aio_session):
        self.token = token
        self.aio_session = aio_session
        self.link = None
        self.calls = 0

    async def get(self, endpoint, json=True):
        print(endpoint)
        async with self.aio_session.get(
            endpoint,
            headers={
                'Authorization': 'token {0}'.format(self.token),
                'Accept': (
                    'application/vnd.github.cloak-preview, '
                    'application/vnd.github.groot-preview+json, '
                    'application/vnd.github.v3+json'
                ),
            }) as resp:

            if resp.status != 200:
                raise Exception(
                    '{0} got status {1}'.format(endpoint, resp.status))

            self.calls += 1
            self.link = resp.headers.get('link')

            if json:
                return await resp.json()
            return await resp.text()

    async def get_all_pages(self, endpoint, key=None):
        req = self.get(endpoint)
        if key is not None:
            out = (await req)[key]
        else:
            out = req

        next_page = self.next_page_url()
        while next_page:
            if key is not None:
                out += await self.get(next_page)[key]
            else:
                out += await self.get(next_page)
            next_page = self.next_page_url()

        self.link = None
        return out

    def next_page_url(self):
        if not self.link:
            return None
        sp = self.link.split(', ')
        for link in sp:
            match = re.match('<(.+)>; rel="next"', link)
            if not match:
                continue
            return match[1]
