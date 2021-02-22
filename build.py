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
    # TODO: We need to unhardcode these:
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
        # If adding more metrics, add their max to max_score (or less to weigh
        # them differently)
        max_score = 50
        score = 0
        # This is all arbitrary, we just need to roughly assign a score.
        comments = pr.get('comments', 0)
        if comments > 5:
            score += 10
        else:
            score += comments * 2

        review_comments = pr.get('review_comments', 0)
        if comments > 3:
            score += 10
        elif comments == 3:
            score += 8
        elif comments == 2:
            score += 4
        else:
            score += 1

        # This isn't out of 10, we intentionally weigh this less
        lines_changed = abs(pr.get('additions', 0) + pr.get('deletions', 0))
        if lines_changed < 10:
            score += 1
        elif lines_changed < 25:
            score += 3
        else:
            score += 5

        # This isn't out of 10, we intentionally weigh this less
        files_changed = pr.get('changed_files', 0)
        if files_changed < 3:
            score += 1
        elif files_changed < 5:
            score += 3
        else:
            score += 5

        # This isn't out of 10, we intentionally weigh this less
        commits = pr.get('commits', 0)
        if commits < 3:
            score += commits
        else:
            score += 5

        return score / max_score

    def score_to_class(score):
        if score > 80:
            return 'danger'
        elif score > 50:
            return 'warning'
        else:
            return 'success'

    for version in VERSIONS:
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

    for pr, score in scores.items():
        scores[pr] = (score / max_score) * 100

    for pr, score in orig_scores.items():
        orig_scores[pr] = (score / max_orig_score) * 100

    out = {
        'backports': backports,
        'originals': originals,
        'scores': scores,
        'orig_scores': orig_scores,
        'score_to_class': score_to_class,
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
