import re
import requests

class GitHubAPICall:
    def __init__(self, token):
        self.token = token
        self.link = None
        self.calls = 0

    def get(self, endpoint):
        r = requests.get(
            endpoint,
            headers={
                'Authorization': 'token {0}'.format(self.token),
                'Accept': (
                    'application/vnd.github.cloak-preview, '
                    'application/vnd.github.groot-preview+json, '
                    'application/vnd.github.v3+json'
                ),
            })

        r.raise_for_status()
        self.calls += 1
        self.link = r.headers.get('link')
        return r

    def get_all_pages(self, endpoint, key=None):
        req = self.get(endpoint)
        if key is not None:
            out = req.json()[key]
        else:
            out = req.json()

        next_page = self.next_page_url()
        while next_page:
            if key is not None:
                out += self.get(next_page).json()[key]
            else:
                out += self.get(next_page).json()
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
