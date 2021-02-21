#!/usr/bin/env python3

import os
import os.path
from staticjinja import Site
import sys

from releasible.github import GitHubAPICall

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

def ctx_aut(template):
    client = GitHubAPICall(GITHUB_TOKEN)
    latest_run = client.get('https://api.github.com/repos/relrod/aut/actions/runs?per_page=1').json()
    jobs_url = '{}?per_page=100'.format(latest_run['workflow_runs'][0]['jobs_url'])
    jobs_req = client.get(jobs_url)
    jobs = jobs_req.json()['jobs']

    next_page = client.next_page_url()
    while next_page:
        jobs += client.get(next_page).json()['jobs']
        next_page = client.next_page_url()

    return {'jobs': jobs}

def ctx_overview(template):
    return {'f': 3}

def base(template):
    out = {}
    tpl_name = os.path.basename(template.filename).replace('.html', '')

    def active_if(name):
        '''Used for sidebar link highlighting'''
        return 'active' if name == tpl_name else ''

    out['active_if'] = active_if

    func = globals().get('ctx_' + tpl_name)
    if func:
        for k, v in func(template).items():
            out[k] = v

    return out

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print('Define $GITHUB_TOKEN first (hint: use a "personal token")')
        sys.exit(1)

    site = Site.make_site(
        searchpath='static',
        outpath='site',
        contexts=[('.*\.html', base)],
    )
    # enable automatic reloading
    site.render(use_reloader=True)
