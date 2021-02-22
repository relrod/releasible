import arrow
from dataclasses import dataclass
from enum import Enum
import packaging.version
import requests
from typing import Optional

class Stage(Enum):
    GENERAL_AVAILABILITY = 1
    BETA = 2
    RELEASE_CANDIDATE = 3

    @staticmethod
    def from_version(version):
        if isinstance(version, packaging.version.Version):
            pre = version.pre
            if pre is None:
                return Stage.GENERAL_AVAILABILITY
            else:
                if pre[0] == 'b':
                    return Stage.BETA
                elif pre[0] == 'rc':
                    return Stage.RELEASE_CANDIDATE
        elif isinstance(version, str):
            if 'b' in version:
                return Stage.BETA
            elif 'rc' in version:
                return Stage.RELEASE_CANDIDATE
            else:
                return Stage.GENERAL_AVAILABILITY
        raise Exception('Cannot determine release stage')

@dataclass(order=False)
class Release:
    product: str
    version: packaging.version.Version
    is_published: bool
    stage: Stage
    date: Optional[arrow.Arrow]

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return self.version == other.version

    def guess_next_version(self):
        public = self.version.public
        if self.stage == Stage.RELEASE_CANDIDATE:
            # If we are a release candidate, the next one isn't.
            # There's not much to do, we're going rc -> ga
            public = public.split('rc')[0]
            return packaging.version.parse(public)
        elif self.stage == Stage.BETA:
            # Impossible to know if it's likely to be beta -> rc or
            # beta -> beta.
            raise Exception('We do not currently try to guess betas')
        else:
            components = [int(x) for x in public.split('.')]
            components[-1] += 1
            components = [str(x) for x in components]
            components[-1] += 'rc1'
            public = '.'.join(components)
            return packaging.version.parse(public)

    def guess_next_date(self):
        # We go back 4 days before the upload (giving us 4 days leeway).
        # Then find the "3rd next monday" to get the next release date. Or
        # for rc, the "1st next monday"
        monday_after_upload = self.date.shift(days=-4).shift(weekday=0)
        weeks_to_shift = 1 if self.stage == Stage.RELEASE_CANDIDATE else 3
        next_date = monday_after_upload.shift(weeks=weeks_to_shift)
        return next_date

    def guess_next_release(self):
        '''
        Attempt to accurately guess the next version of this Release, and
        return a new Release with the result.
        '''
        new_version = self.guess_next_version()
        new_date = self.guess_next_date()
        return Release(
            self.product,
            new_version,
            False,
            Stage.from_version(new_version),
            new_date)

class PyPI:
    def __init__(self, pkg):
        url = 'https://pypi.python.org/pypi/{0}/json'.format(pkg)
        r = requests.get(url)
        r.raise_for_status()
        self.json = r.json()
        self.pkg = pkg

    def latest(self, version):
        versions = []
        # This could be more efficient, we construct a lot of objects for no
        # reason here
        for release, details in self.json['releases'].items():
            if not details or details[0]['yanked']:
                # Skip any yanked releases, we don't count them
                continue

            if release.startswith(version):
                versions.append(packaging.version.parse(release))

        versions = sorted(versions)

        if not versions:
            return

        latest = versions[-1]
        details = self.json['releases'][latest.public][0]
        r = Release(
            self.pkg,
            latest,
            True,
            Stage.from_version(latest),
            arrow.get(details['upload_time_iso_8601']))

        return r
