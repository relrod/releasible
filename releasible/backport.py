import re
from releasible.github import GitHubAPICall

PULL_URL_RE = re.compile(r'(?P<user>\S+)/(?P<repo>\S+)#(?P<ticket>\d+)')
PULL_HTTP_URL_RE = re.compile(r'https?://(?:www\.|)github.com/(?P<user>\S+)/(?P<repo>\S+)/pull/(?P<ticket>\d+)')
PULL_BACKPORT_IN_TITLE = re.compile(r'.*\(#?(?P<ticket1>\d+)\)|\(backport of #?(?P<ticket2>\d+)\).*', re.I)
PULL_CHERRY_PICKED_FROM = re.compile(r'\(?cherry(?:\-| )picked from(?:commit|) (?P<hash>\w+)(?:\)|\.|$)')
TICKET_NUMBER = re.compile(r'(?:^|\s)#(\d+)')

def normalize_pr_url(pr, allow_non_ansible_ansible=False, only_number=False):
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
    if isinstance(pr, dict):
        url = pr.get('html_url')
        if url is None:
            raise Exception('dict did not have html_url key')
        return url

    if str(pr).isnumeric():
        if only_number:
            return int(pr)
        return 'https://github.com/ansible/ansible/pull/{0}'.format(pr)

    # Allow for forcing ansible/ansible
    if not allow_non_ansible_ansible and 'ansible/ansible' not in pr:
        raise Exception('Non ansible/ansible repo given where not expected')

    re_match = PULL_HTTP_URL_RE.match(pr)
    if re_match:
        if only_number:
            return int(re_match.group('ticket'))
        return 'https://github.com/{0}/{1}/pull/{2}'.format(
            re_match.group('user'),
            re_match.group('repo'),
            re_match.group('ticket'))

    re_match = PULL_URL_RE.match(pr)
    if re_match:
        if only_number:
            return int(re_match.group('ticket'))
        return 'https://github.com/{0}/{1}/pull/{2}'.format(
            re_match.group('user'),
            re_match.group('repo'),
            re_match.group('ticket'))

    raise Exception('Did not understand given PR')


#class BackportFinder(GitHubAPICall):

