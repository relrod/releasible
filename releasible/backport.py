import asyncio
import re
from releasible.github import GitHubAPICall
from releasible.model.pullrequest import Backport, PullRequest
from unidiff import PatchSet

PULL_URL_RE = re.compile(r'(?P<user>\S+)/(?P<repo>\S+)#(?P<ticket>\d+)')
PULL_HTTP_URL_RE = re.compile(r'https?://(?:www\.|)github\.com/(?P<user>\S+)/(?P<repo>\S+)/pull/(?P<ticket>\d+)')
COMMIT_HTTP_URL_RE = re.compile(r'https?://(?:www\.|)github\.com/(?P<user>\S+)/(?P<repo>\S+)/commit/(?P<hash>\w+)')
PULL_BACKPORT_IN_TITLE = re.compile(r'\((?:backport of |)#?(?P<ticket>\d+)\)', re.I)
PULL_CHERRY_PICKED_FROM = re.compile(r'\(?cherry(?:\-| )picked from(?: commit|) (?P<hash>\w+)(?:\)|\.|$)')
TICKET_NUMBER = re.compile(r'(?:^|\s)#(?P<ticket>\d+)')

def normalize_pr_url(
        pr,
        allow_non_ansible_ansible=False,
        only_number=False,
        api=False):
    '''
    Given a JSON response (dict), or a string containing a PR number, PR URL,
    or internal PR URL (e.g. ansible-collections/community.general#1234),
    return either a full github URL to the PR (if only_number is False),
    or an int containing the PR number (if only_number is True).

    Throws if it can't parse the input.

    >>> normalize_pr_url('https://github.com/ansible/ansible/pull/1234')
    'https://github.com/ansible/ansible/pull/1234'

    >>> normalize_pr_url('foo/bar#1234', allow_non_ansible_ansible=True)
    'https://github.com/foo/bar/pull/1234'
    '''
    def url(user, repo, ticket):
        if api:
            return 'https://api.github.com/repos/{0}/{1}/pulls/{2}'.format(
                user,
                repo,
                ticket)
        else:
            return 'https://github.com/{0}/{1}/pull/{2}'.format(
                user,
                repo,
                ticket)

    if isinstance(pr, dict):
        url = pr.get('url') if api else pr.get('html_url')
        if url is None:
            raise Exception('dict did not have html_url key')
        if '/pull' not in url:
            raise Exception('dict appears to not be a pull request')
        return url

    if str(pr).isnumeric():
        if only_number:
            return int(pr)
        return url('ansible', 'ansible', pr)

    # Allow for forcing ansible/ansible
    if not allow_non_ansible_ansible and 'ansible/ansible' not in pr:
        raise Exception('Non ansible/ansible repo given where not expected')

    re_match = PULL_HTTP_URL_RE.match(pr)
    if re_match:
        if only_number:
            return int(re_match.group('ticket'))
        return url(
            re_match.group('user'),
            re_match.group('repo'),
            re_match.group('ticket'))

    re_match = PULL_URL_RE.match(pr)
    if re_match:
        if only_number:
            return int(re_match.group('ticket'))
        return url(
            re_match.group('user'),
            re_match.group('repo'),
            re_match.group('ticket'))

    raise Exception('Did not understand given PR')

class BackportFinder(GitHubAPICall):
    async def prs_for_commit(self, sha):
        # Find the repos associated with the commit
        query = 'hash:{0} org:ansible org:ansible-collections is:public'.format(
            sha)
        url = 'https://api.github.com/search/commits?per_page=100&q={0}'.format(
            query)
        res = (await self.get(url)).get('items')

        if not res:
            return []

        # Find the PRs in those repos
        prs = []
        for result in res:
            repo = result.get('repository', {}).get('full_name', {})
            if not repo:
                continue
            url = 'https://api.github.com/repos/{0}/commits/{1}/pulls?per_page=100'.format(
                repo,
                sha)
            prs += await self.get(url)

        # We have to query the actual pull request endpoint, otherwise we lack
        # the fields we use later for scoring (comments, review_comments, etc.)
        # We use the html_url because the PR might be outside of ansible/ansible
        # and get_pr will call normalize_pr_url which can work on html urls.
        return await asyncio.gather(
            *[self.get_pr(pr['html_url']) for pr in prs])

    async def get_backports_for_version(self, version):
        out = []
        query = 'is:pr is:open repo:ansible/ansible label:backport '
        query += '-label:waiting_on_upstream -label:on_hold '
        query += 'base:stable-{0}'.format(version)

        prs = await self.get_all_pages(
            'https://api.github.com/search/issues?per_page=100&'
            'sort=created&q={0}'.format(query),
            key='items')

        cors = [self.get_pr(pr['number']) for pr in prs]
        return await asyncio.gather(*cors)


    async def get_pr(self, pr, allow_non_ansible_ansible=True) -> PullRequest:
        pr_dict = await self.get(
            normalize_pr_url(
                pr,
                allow_non_ansible_ansible=allow_non_ansible_ansible,
                api=True))
        pr_diff = PatchSet(await self.get(pr_dict['diff_url'], json=False))
        return PullRequest(pr_dict, pr_diff)

    async def guess_original_pr(self, q):
        '''
        Do magic. It will search the PR (the newest PR - the backport) and try
        to find where it originated.

        First it will search in the title. Some titles include things like
        "foo bar change (#12345)" or "foo bar change (backport of #54321)"
        so we search for those and pull them out.

        Next it will scan the body of the PR and look for:
          - cherry-pick reference lines (e.g. "cherry-picked from commit XXXXX")
          - other PRs (#nnnnnn) and (foo/bar#nnnnnnn)
          - full URLs to other PRs

        It will take all of the above, and return a list of "possibilities",
        which is a list of dicts (API results) for each potential PR. The head
        of the PR is most likely candidate, if you can only use one result, but
        correctness is not guaranteed.
        '''

        if isinstance(q, PullRequest):
            pr = q
        else:
            pr = await self.get_pr(q)

        possibilities = []

        # 1. Try searching for it in the title.
        title_search = PULL_BACKPORT_IN_TITLE.search(pr.pr['title'])
        if title_search:
            ticket = title_search.group('ticket')
            try:
                possibility = await self.get_pr(ticket)
                if possibility.number != pr.number:
                    possibilities.append(possibility)
            except Exception:
                pass

        # 2. Search for clues in the body of the PR
        body_lines = pr.pr['body'].split('\n')
        for line in body_lines:
            # a. Try searching for a `git cherry-pick` line
            cherrypick = PULL_CHERRY_PICKED_FROM.match(line)
            if cherrypick:
                prs = await self.prs_for_commit(cherrypick.group('hash'))
                for possibility in prs:
                    if possibility.number != pr.number:
                        possibilities.append(possibility)
                continue

            # b. Try searching for a full link to another commit
            commit_link = COMMIT_HTTP_URL_RE.search(line)
            if commit_link:
                prs = await self.prs_for_commit(commit_link.group('hash'))
                for possibility in prs:
                    if possibility.number != pr.number:
                        possibilities.append(possibility)
                continue

            # c. Try searching for other referenced PRs (by #nnnnn or full URL)
            tickets = [
                ('ansible', 'ansible', ticket)
                for ticket in TICKET_NUMBER.findall(line)
            ]
            tickets.extend(PULL_HTTP_URL_RE.findall(line))
            tickets.extend(PULL_URL_RE.findall(line))
            if tickets:
                for ticket in tickets:
                    # Is it a PR (even if not in ansible/ansible)?
                    try:
                        pr_url = '{0}/{1}#{2}'.format(ticket[0], ticket[1], ticket[2])
                        possibility = await self.get_pr(pr_url)
                        if possibility.number != pr.number:
                            possibilities.append(possibility)
                    except Exception:
                        pass
                continue  # Future-proofing

        return possibilities
