import re
import requests

class GitHubAPICall:
    def __init__(self, token):
        self.token = token
        self.link = None

    def get(self, endpoint):
        r = requests.get(
            endpoint,
            headers={
                'Authorization': 'token {0}'.format(self.token),
            })

        r.raise_for_status()
        self.link = r.headers.get('link')
        return r

    def next_page_url(self):
        if not self.link:
            return None
        sp = self.link.split(', ')
        for link in sp:
            match = re.match('<(.+)>; rel="next"', link)
            if not match:
                continue
            return match[1]
