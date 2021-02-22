import pytest
from releasible.backport import *

@pytest.fixture
def finder():
    import os
    token = os.environ.get('GITHUB_TOKEN_RO')
    return BackportFinder(token)

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
def test_prs_for_commit(finder):
    prs = finder.prs_for_commit('997b2d2a1955ccb4e70f805c18dc3e227e86c678')
    assert len(prs) == 1
    assert prs[0]['number'] == 73467

@pytest.mark.vcr(filter_headers=['authorization'])
def test_guess_original_pr(finder):
    # Has (#nnnnn) in title
    original_for_73544 = finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73544')
    assert original_for_73544[0]['number'] == 73541

    # Has a cherry-pick line
    original_for_73493 = finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73493')
    assert original_for_73493[0]['number'] == 73487

    # Has a "Backport of" link
    original_for_73067 = finder.guess_original_pr(
        'https://github.com/ansible/ansible/pull/73067')
    assert original_for_73067[0]['number'] == 55
