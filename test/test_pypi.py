import arrow
import packaging.version
from releasible.pypi import *

import pytest

@pytest.fixture
def release_ga():
    return Release(
        'ansible',
        packaging.version.parse('2.9.18'),
        True,
        Stage.GENERAL_AVAILABILITY,
        arrow.get('2021-02-18T22:53:20.617927+00:00'))

@pytest.fixture
def release_rc():
    return Release(
        'ansible',
        packaging.version.parse('2.9.18rc1'),
        True,
        Stage.RELEASE_CANDIDATE,
        arrow.get('2021-02-09T02:53:19.138189+00:00'))

def test_guess_next_version(release_ga, release_rc):
    assert release_ga.guess_next_version() == \
        packaging.version.Version('2.9.19rc1')

    assert release_rc.guess_next_version() == \
        packaging.version.Version('2.9.18')

def test_guess_next_version(release_ga, release_rc):
    assert release_ga.guess_next_date() == \
        arrow.get('2021-03-08T22:53:20.617927+00:00')

    assert release_rc.guess_next_date() == \
        arrow.get('2021-02-15T02:53:19.138189+00:00')
