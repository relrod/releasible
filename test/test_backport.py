from releasible.backport import *

def test_normalize_pr_url():
    ANSI_URL = 'https://github.com/ansible/ansible/pull/1234'
    CG_URL = 'https://github.com/ansible-collections/community.general/pull/1176'

    demo_response = {
        'html_url': ANSI_URL,
    }

    assert normalize_pr_url('1234') == ANSI_URL
    assert normalize_pr_url(demo_response) == ANSI_URL
    assert normalize_pr_url('ansible/ansible#1234') == ANSI_URL
    assert normalize_pr_url(ANSI_URL) == ANSI_URL
    assert normalize_pr_url(ANSI_URL + '#foo') == ANSI_URL
    assert normalize_pr_url(ANSI_URL + '?foo=8') == ANSI_URL
    assert normalize_pr_url(ANSI_URL, allow_non_ansible_ansible=True) == ANSI_URL
    assert normalize_pr_url(ANSI_URL, only_number=True) == 1234

    assert normalize_pr_url(CG_URL, allow_non_ansible_ansible=True) == CG_URL
    assert normalize_pr_url(
        'ansible-collections/community.general#1176',
        allow_non_ansible_ansible=True) == CG_URL

    assert normalize_pr_url(
        CG_URL,
        allow_non_ansible_ansible=True,
        only_number=True) == 1176
