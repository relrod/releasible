#!/usr/bin/env python3

import aiohttp
import asyncio
import os
import os.path
from staticjinja import Site
import sys

from releasible.github import GitHubAPICall
from releasible.backport import BackportFinder
from releasible.model.pullrequest import Backport

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN_RO')
VERSIONS = ['2.8', '2.9', '2.10']

async def ctx_aut(template):
    aio_session = aiohttp.ClientSession()
    client = GitHubAPICall(GITHUB_TOKEN, aio_session)
    latest_run = await client.get('https://api.github.com/repos/relrod/aut/actions/runs?per_page=1')
    jobs_url = '{}?per_page=100'.format(latest_run['workflow_runs'][0]['jobs_url'])
    jobs_req = await client.get(jobs_url)
    jobs = jobs_req['jobs']

    next_page = client.next_page_url()
    while next_page:
        next_resp = await client.get(next_page)
        jobs += next_resp['jobs']
        next_page = client.next_page_url()

    await aio_session.close()
    return {'jobs': jobs}

async def ctx_backports(template):
    backports = {}
    aio_session = aiohttp.ClientSession()
    bf = BackportFinder(GITHUB_TOKEN, aio_session)

    max_risk = 0
    max_orig_risk = 0

    for version in VERSIONS:
        prs = await bf.get_backports_for_version(version)
        backports[version] = []

        cors = [bf.guess_original_pr(pr) for pr in prs]
        originals = await asyncio.gather(*cors)

        # We need to bail out/error if this is never true, because otherwise
        # we'd show PRs that belong to originals that don't make sense.
        assert len(prs) == len(originals)

        for idx, pr in enumerate(prs):
            original = originals[idx]
            if original:
                original = original[0]
            else:
                original = None
            bp = Backport(pr.pr, pr.diff, original)
            backports[version].append(bp)

            # While we're here track global max risks
            if bp.risk > max_risk:
                max_risk = bp.risk

            if bp.original is not None:
                if bp.original.risk > max_orig_risk:
                    max_orig_risk = bp.original.risk

    out = {
        'backports': backports,
        'max_risk': max_risk,
        'max_orig_risk': max_orig_risk,
    }

    await aio_session.close()
    return out

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
        if asyncio.iscoroutinefunction(func):
            res = asyncio.run(func(template))
        else:
            res = func(template)
        for k, v in res.items():
            out[k] = v

    return out

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print('Define $GITHUB_TOKEN_RO first (hint: use a "personal token")')
        sys.exit(1)

    site = Site.make_site(
        searchpath='static',
        outpath='site',
        contexts=[(r'.*\.html', base)],
    )
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        site.render(use_reloader=False)
    else:
        site.render(use_reloader=True)
