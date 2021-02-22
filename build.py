#!/usr/bin/env python3

import aiohttp
import asyncio
import os
import os.path
from staticjinja import Site
import sys

from releasible.github import GitHubAPICall
from releasible.backport import BackportFinder

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN_RO')

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
    # TODO: We need to unhardcode these:
    versions = ['2.10']
    backports = {}
    originals = {}
    aio_session = aiohttp.ClientSession()
    bf = BackportFinder(GITHUB_TOKEN, aio_session)

    scores = {}
    orig_scores = {}
    max_score = 0
    max_orig_score = 0

    def score_pr(pr):
        '''Assign a risk score to the given PR.'''
        score = 0
        score += pr.get('comments', 0) * 0.45
        score += pr.get('review_comments', 0) * 0.45
        score += abs(pr.get('additions', 0) - pr.get('deletions', 0)) * 0.5
        score += pr.get('changed_files', 0) * 0.5
        score /= 4 # divide by number of metrics, create an average
        print((pr.get('number'), pr.get('comments'), pr.get('review_comments'), pr.get('additions'), pr.get('deletions'), pr.get('changed_files'), score))
        return score

    for version in versions:
        prs = await bf.get_backports_for_version(version)
        backports[version] = prs

        cors = [bf.guess_original_pr(pr) for pr in prs]
        original_awaited = await asyncio.gather(*cors)

        for idx, pr in enumerate(prs):
            score = score_pr(pr)
            scores[pr['number']] = score
            if score > max_score:
                max_score = score

            orig = original_awaited[idx]
            if not orig:
                continue
            orig = orig[0]
            originals[pr['number']] = orig
            score = score_pr(orig)
            orig_scores[pr['number']] = score
            if score > max_orig_score:
                max_orig_score = score

    print(orig_scores)

    for pr, score in scores.items():
        scores[pr] = (score / max_score) * 100

    for pr, score in orig_scores.items():
        orig_scores[pr] = (score / max_orig_score) * 100

    print(orig_scores)

    out = {
        'backports': backports,
        'originals': originals,
        'scores': scores,
        'orig_scores': orig_scores,
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
    # enable automatic reloading
    site.render(use_reloader=True)
