from dataclasses import dataclass
import functools
from unidiff import PatchSet

HIGH_WEIGHTED_PATHS = (
    # ansible{,-base,-core}
    'lib',

    # ansible-test
    'test/runner',
    'test/utils',
    'test/lib',

    # legal
    'licenses',

    # releng
    'requirements.txt',
    'packaging',
    'setup.py',
    'MANIFEST.in',
    'Makefile',
)

@dataclass
class PullRequest:
    '''
    This contains all of the information we care about when rendering pull
    requests in the UI. In addition to the original PR, it contains fields like
    weight, diff information, CI status, etc.
    '''
    pr: dict
    diff: PatchSet

    @property
    def risk(self):
        '''Assign a risk score to the PR.'''
        # Add 10 points to max_score for each risk factor/metric added, even if
        # the added metric is worth less than 10 because it's weighted less.
        max_score = 60
        score = 0

        # This is all arbitrary, we just need to roughly assign a score.

        # 1: How many comments are there on the PR?
        comments = self.pr.get('comments', 0)
        if comments > 5:
            score += 10
        else:
            score += comments * 2

        # 2: How many review comments are there?
        review_comments = self.pr.get('review_comments', 0)
        if comments > 3:
            score += 10
        elif comments == 3:
            score += 8
        elif comments == 2:
            score += 4
        else:
            score += 1

        # 3: How many lines were added + removed?
        # This isn't out of 10, we intentionally weigh this less
        lines_changed = abs(self.pr.get('additions', 0) + self.pr.get('deletions', 0))
        if lines_changed < 10:
            score += 1
        elif lines_changed < 25:
            score += 3
        else:
            score += 5

        # 4: How many files were changed?
        # This isn't out of 10, we intentionally weigh this less
        files_changed = self.pr.get('changed_files', 0)
        if files_changed < 3:
            score += 1
        elif files_changed < 5:
            score += 3
        else:
            score += 5

        # 5: How many commits are in the PR?
        # This isn't out of 10, we intentionally weigh this less
        commits = self.pr.get('commits', 0)
        if commits < 3:
            score += commits
        else:
            score += 5

        # 6: How many high-weighted files were changed?
        # We only handle high-weighted here. Everything else is handled by the
        # global metrics above (changed_files and additions/deletions on the
        # PR).
        hw_files_changed = 0
        hw_lines_changed = 0
        for changed_file in self.diff:
            for path in HIGH_WEIGHTED_PATHS:
                if changed_file.path.startswith(path):
                    hw_files_changed += 1
                    hw_lines_changed += changed_file.added + changed_file.removed
        if hw_files_changed > 5 and hw_lines_changed > 25:
            score += 10
        elif hw_files_changed > 2 and hw_lines_changed > 10:
            score += 7
        elif hw_files_changed > 0:
            if hw_lines_changed > 20:
                score += 5
            else:
                score += 3

        return score / max_score

    def relative_risk(self, max_risk):
        '''
        Given a max risk for a list of PullRequests, return this PR's relative
        risk as a percentage.
        '''
        return (self.risk / max_risk) * 100

    @property
    def number(self):
        if 'number' not in self.pr:
            raise Exception(
                'PullRequest instantiated with bad dict: did not contain '
                '"number" field')
        return self.pr['number']

    @property
    def is_missing_changelog(self):
        needs_changelog = False

        for p in self.diff:
            if p.path.startswith('changelogs/fragments/'):
                return False

            if p.path.startswith(HIGH_WEIGHTED_PATHS):
                needs_changelog = True

        return needs_changelog

    @property
    def is_docs(self):
        labels = [x['name'] for x in self.pr.get('labels', [])]
        if all(x.path.startswith('docs/docsite') for x in self.diff):
            if 'docs' in labels:
                return True
        return False

    @property
    def needs_info(self):
        labels = [x['name'] for x in self.pr.get('labels', [])]
        return 'needs_info' in labels

@dataclass
class Backport(PullRequest):
    original: PullRequest
