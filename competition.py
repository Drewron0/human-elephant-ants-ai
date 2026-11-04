"""Fixed rules shared by the competition clock, board and standings."""
import time

TIME_LIMIT = 240
AI_MODEL = 'proposed_d6'
SEARCH_DEPTH = 6


def calculate_score(solved, steps, elapsed_seconds):
    if not solved or elapsed_seconds >= TIME_LIMIT:
        return 0
    return max(0, 1000 - 10 * steps)


def challenge_key(scenario):
    return f'{scenario.id}:{AI_MODEL}:d{SEARCH_DEPTH}:t{TIME_LIMIT}:v1'


class CompetitionAttempt:
    def __init__(self, clock=None):
        self.clock = clock or time.monotonic
        self.started_at = self.clock()
        self.ended_at = None

    @property
    def elapsed_seconds(self):
        end = self.clock() if self.ended_at is None else self.ended_at
        return max(0.0, end - self.started_at)

    @property
    def remaining_seconds(self):
        return max(0.0, TIME_LIMIT - self.elapsed_seconds)

    @property
    def expired(self):
        return self.elapsed_seconds >= TIME_LIMIT

    def finish(self, solved, steps):
        if self.ended_at is None:
            self.ended_at = self.clock()
        elapsed = self.elapsed_seconds
        solved = bool(solved and elapsed < TIME_LIMIT)
        return {'solved': solved, 'steps': steps, 'elapsed_seconds': elapsed,
                'score': calculate_score(solved, steps, elapsed)}
