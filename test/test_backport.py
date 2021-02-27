import aiohttp
import pytest
import re
from releasible.backport import *
from typing import Dict

@pytest.fixture
async def finder():
    import os
    aio_session = aiohttp.ClientSession()
    token = os.environ.get('GITHUB_TOKEN_RO')
    yield BackportFinder(token, aio_session)
    await aio_session.close()

def test_normalize_pr_url():
    ANSI_URL = 'https://github.com/ansible/ansible/pull/1234'
    ANSI_API_URL = 'https://api.github.com/repos/ansible/ansible/pulls/1234'
    CG_URL = 'https://github.com/ansible-collections/community.general/pull/1176'

    demo_response = {
        'html_url': ANSI_URL,
    }

    assert normalize_pr_url('1234') == ANSI_URL
    assert normalize_pr_url(demo_response) == ANSI_URL
    assert normalize_pr_url('ansible/ansible#1234') == ANSI_URL
    assert normalize_pr_url('ansible/ansible#1234', only_number=True) == 1234
    assert normalize_pr_url(ANSI_URL) == ANSI_URL
    assert normalize_pr_url(ANSI_URL, api=True) == ANSI_API_URL
    assert normalize_pr_url(ANSI_URL + '#foo') == ANSI_URL
    assert normalize_pr_url(ANSI_URL + '?foo=8') == ANSI_URL
    assert normalize_pr_url(ANSI_URL, allow_non_ansible_ansible=True) == ANSI_URL
    assert normalize_pr_url(ANSI_URL, only_number=True) == 1234
    assert normalize_pr_url('1234', only_number=True) == 1234

    assert normalize_pr_url(CG_URL, allow_non_ansible_ansible=True) == CG_URL
    assert normalize_pr_url(
        'ansible-collections/community.general#1176',
        allow_non_ansible_ansible=True) == CG_URL

    assert normalize_pr_url(
        CG_URL,
        allow_non_ansible_ansible=True,
        only_number=True) == 1176

@pytest.mark.vcr(filter_headers=['authorization'])
@pytest.mark.asyncio
async def test_prs_for_commit(finder):
    prs = await finder.prs_for_commit(
        '997b2d2a1955ccb4e70f805c18dc3e227e86c678')
    assert len(prs) == 1
    assert prs[0].number == 73467

@pytest.mark.vcr(filter_headers=['authorization'])
@pytest.mark.asyncio
async def test_guess_original_pr(finder):
    # Has (#nnnnn) in title
    original_for_73544 = await finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73544')
    assert original_for_73544[0].number == 73541

    # Has a cherry-pick line
    original_for_73493 = await finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73493')
    assert original_for_73493[0].number == 73487

    # Has a "Backport of" link
    original_for_73067 = await finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73067')
    assert original_for_73067[0].number == 55

    # Full, out-of-repo commit URL and later self-reference
    original_for_73556 = await finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73556')
    assert original_for_73556[0].number == 82

def _regex_test(regex: re.Pattern, test: str, groups: Dict[str, str]) -> None:
    res = regex.search(test)
    assert res is not None

    for name, expected in groups.items():
        assert res.group(name) == expected

def test_PULL_URL_RE():
    _regex_test(
        PULL_URL_RE,
        'foo/bar#12345',
        dict(user='foo', repo='bar', ticket='12345'))

    _regex_test(
        PULL_URL_RE,
        'ansible-collections/ansible.posix#12345',
        dict(user='ansible-collections', repo='ansible.posix', ticket='12345'))

    _regex_test(
        PULL_URL_RE,
        'ansible-collections/ansible.posix#1',
        dict(user='ansible-collections', repo='ansible.posix', ticket='1'))

    _regex_test(
        PULL_URL_RE,
        'a/b#1',
        dict(user='a', repo='b', ticket='1'))

def test_PULL_HTTP_URL_RE():
    _regex_test(
        PULL_HTTP_URL_RE,
        'https://www.github.com/ansible/ansible/pull/73544',
        dict(user='ansible', repo='ansible', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'https://www.github.com/ansible-collections/ansible.posix/pull/73544',
        dict(user='ansible-collections', repo='ansible.posix', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'https://github.com/ansible/ansible/pull/73544',
        dict(user='ansible', repo='ansible', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'http://www.github.com/ansible/ansible/pull/73544',
        dict(user='ansible', repo='ansible', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'http://github.com/ansible/ansible/pull/73544',
        dict(user='ansible', repo='ansible', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'https://www.github.com/ansible/ansible/pull/73544#foo',
        dict(user='ansible', repo='ansible', ticket='73544'))

    _regex_test(
        PULL_HTTP_URL_RE,
        'https://www.github.com/ansible/ansible/pull/73544?foo',
        dict(user='ansible', repo='ansible', ticket='73544'))

def test_COMMIT_HTTP_URL_RE():
    _regex_test(
        COMMIT_HTTP_URL_RE,
        'https://github.com/ansible/ansible/commit/2377a0a7765fc9121d129abb15889bc100647e0a',
        dict(
            user='ansible',
            repo='ansible',
            hash='2377a0a7765fc9121d129abb15889bc100647e0a'))

    _regex_test(
        COMMIT_HTTP_URL_RE,
        'http://github.com/ansible/ansible/commit/2377a0a7765fc9121d129abb15889bc100647e0a',
        dict(
            user='ansible',
            repo='ansible',
            hash='2377a0a7765fc9121d129abb15889bc100647e0a'))

    _regex_test(
        COMMIT_HTTP_URL_RE,
        'https://www.github.com/ansible/ansible/commit/2377a0a7765fc9121d129abb15889bc100647e0a',
        dict(
            user='ansible',
            repo='ansible',
            hash='2377a0a7765fc9121d129abb15889bc100647e0a'))

    _regex_test(
        COMMIT_HTTP_URL_RE,
        'https://github.com/ansible-collections/ansible.posix/commit/e1dad76ccbe1f1f43babb1774e407d8583e61405',
        dict(
            user='ansible-collections',
            repo='ansible.posix',
            hash='e1dad76ccbe1f1f43babb1774e407d8583e61405'))

def test_PULL_BACKPORT_IN_TITLE():
    _regex_test(
        PULL_BACKPORT_IN_TITLE,
        '(backport of #12345)',
        dict(ticket='12345'))

    _regex_test(
        PULL_BACKPORT_IN_TITLE,
        'Foo bar (backport of #54321)',
        dict(ticket='54321'))

    _regex_test(
        PULL_BACKPORT_IN_TITLE,
        'Foo bar (#54321)',
        dict(ticket='54321'))

    _regex_test(
        PULL_BACKPORT_IN_TITLE,
        '(#54321) Foo bar',
        dict(ticket='54321'))

    _regex_test(
        PULL_BACKPORT_IN_TITLE,
        '(Backport Of #54321) Foo bar',
        dict(ticket='54321'))

def test_PULL_CHERRY_PICKED_FROM():
    _regex_test(
        PULL_CHERRY_PICKED_FROM,
        '(cherry picked from commit 0a8d5c098367a58eaff10fd5b3868f099c1e17a7)',
        dict(hash='0a8d5c098367a58eaff10fd5b3868f099c1e17a7'))

    _regex_test(
        PULL_CHERRY_PICKED_FROM,
        '(cherry picked from 0a8d5c098367a58eaff10fd5b3868f099c1e17a7)',
        dict(hash='0a8d5c098367a58eaff10fd5b3868f099c1e17a7'))

    _regex_test(
        PULL_CHERRY_PICKED_FROM,
        '(cherry-picked from 0a8d5c098367a58eaff10fd5b3868f099c1e17a7)',
        dict(hash='0a8d5c098367a58eaff10fd5b3868f099c1e17a7'))

    _regex_test(
        PULL_CHERRY_PICKED_FROM,
        '(cherry-picked from commit 0a8d5c098367a58eaff10fd5b3868f099c1e17a7)',
        dict(hash='0a8d5c098367a58eaff10fd5b3868f099c1e17a7'))

def test_TICKET_NUMBER():
    _regex_test(
        TICKET_NUMBER,
        '#12345',
        dict(ticket='12345'))

    _regex_test(
        TICKET_NUMBER,
        '    #12345',
        dict(ticket='12345'))

    _regex_test(
        TICKET_NUMBER,
        '\t#12345',
        dict(ticket='12345'))
