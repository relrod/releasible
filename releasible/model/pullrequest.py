from dataclasses import dataclass
import functools
from unidiff import PatchSet

@dataclass
class PullRequest:
    '''
    This contains all of the information we care about when rendering pull
    requests in the UI. In addition to the original PR, it contains fields like
    weight, diff information, CI status, etc.
    '''
    pr: dict

    @property
    def risk(self):
        '''Assign a risk score to the PR.'''
        # If adding more metrics, add their max to max_score (or less to weigh
        # them differently)
        max_score = 50
        score = 0
        # This is all arbitrary, we just need to roughly assign a score.
        comments = self.pr.get('comments', 0)
        if comments > 5:
            score += 10
        else:
            score += comments * 2

        review_comments = self.pr.get('review_comments', 0)
        if comments > 3:
            score += 10
        elif comments == 3:
            score += 8
        elif comments == 2:
            score += 4
        else:
            score += 1

        # This isn't out of 10, we intentionally weigh this less
        lines_changed = abs(self.pr.get('additions', 0) + self.pr.get('deletions', 0))
        if lines_changed < 10:
            score += 1
        elif lines_changed < 25:
            score += 3
        else:
            score += 5

        # This isn't out of 10, we intentionally weigh this less
        files_changed = self.pr.get('changed_files', 0)
        if files_changed < 3:
            score += 1
        elif files_changed < 5:
            score += 3
        else:
            score += 5

        # This isn't out of 10, we intentionally weigh this less
        commits = self.pr.get('commits', 0)
        if commits < 3:
            score += commits
        else:
            score += 5

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

@dataclass
class Backport(PullRequest):
    original: PullRequest
