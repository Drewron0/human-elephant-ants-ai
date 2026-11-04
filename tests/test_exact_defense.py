import json
import threading
import unittest
from queue import Queue
from functools import lru_cache
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_engine import get_exact_defender_reply, SearchTelemetry
from game_logic import GameState, Piece
from puzzle_logic import verify_puzzle, puzzle_position_key, make_puzzle_move, PuzzleScenario
from views.puzzle_game_view import PuzzleGameView


class TestExactDefender(unittest.TestCase):
    def test_supplied_position_cannot_be_won_early_against_the_exact_reply(self):
        state = GameState(6, custom_setup=True)
        pieces = [(4, 0, 0, 'A'), (5, 0, 0, 'H'), (5, 1, 0, 'E'),
                  (1, 3, 1, 'E'), (4, 5, 1, 'H')]
        for r, c, owner, pt in pieces:
            state.board[r][c] = Piece(owner, pt)
        make_puzzle_move(state, (4, 0), (3, 1))
        reply = get_exact_defender_reply(state, 23)
        self.assertEqual(reply['status'], 'PROVEN')
        self.assertEqual(reply['proof_horizon'], 7)
        make_puzzle_move(state, *reply['move'])

        # Independent boolean AND/OR solver over piece-position tuples, without
        # GameState or the production verifier, checks every legal player reply.
        owners = (0, 0, 0, 1, 1)
        suits = ('A', 'H', 'E', 'E', 'H')
        beats = {'A': 'E', 'E': 'H', 'H': 'A'}
        positions = tuple(next((r * 6 + c for r, row in enumerate(state.board)
                                for c, p in enumerate(row)
                                if p and p.owner == owner and p.p_type == pt), -1)
                          for owner, pt in zip(owners, suits))
        neighbors = {p: tuple(r * 6 + c for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                              if dr or dc for r, c in [(p // 6 + dr, p % 6 + dc)]
                              if 0 <= r < 6 and 0 <= c < 6) for p in range(36)}

        @lru_cache(maxsize=None)
        def forced(position, turn, remaining):
            if any(position[i] == 5 for i in range(3)):
                return True
            if any(position[i] == 30 for i in (3, 4)) or all(position[i] < 0 for i in range(3)):
                return False
            if min(max(position[i] // 6, 5 - position[i] % 6)
                   for i in range(3) if position[i] >= 0) > remaining:
                return False
            occupied = {p: i for i, p in enumerate(position) if p >= 0}
            children = []
            for i, p in enumerate(position):
                if p < 0 or owners[i] != turn:
                    continue
                for dest in neighbors[p]:
                    victim = occupied.get(dest)
                    if victim is not None and (owners[victim] == turn or beats[suits[i]] != suits[victim]):
                        continue
                    child = list(position)
                    child[i] = dest
                    if victim is not None:
                        child[victim] = -1
                    distance = max(dest // 6, 5 - dest % 6) if turn == 0 else max(5 - dest // 6, dest % 6)
                    children.append((distance, tuple(child)))
            if not children:
                return False if turn == 0 else forced(position, 0, remaining)
            children.sort()
            if turn == 0:
                return any(forced(child, 1, remaining - 1) for _, child in children)
            return all(forced(child, 0, remaining) for _, child in children)

        self.assertFalse(forced(positions, 0, 6))  # No win in seven total player moves.
        self.assertTrue(forced(positions, 0, 7))   # Eight remains achievable.

    def position(self):
        state = GameState(3, custom_setup=True)
        state.board[0][1] = Piece(0, 'H')
        state.board[1][2] = Piece(1, 'H')
        state.current_turn = 1
        return state

    def test_exact_reply_blocks_an_immediate_win_and_maximizes_delay(self):
        state = self.position()
        before = state.to_dict()
        reply = get_exact_defender_reply(state, remaining_steps=5)
        self.assertEqual(reply['status'], 'PROVEN')
        self.assertEqual(reply['move'], ((1, 2), (0, 2)))
        self.assertEqual(reply['proof_horizon'], 2)
        self.assertEqual(state.to_dict(), before)
        child = state.clone()
        make_puzzle_move(child, *reply['move'])
        pieces = [(r, c, p.owner, p.p_type) for r, row in enumerate(child.board)
                  for c, p in enumerate(row) if p]
        self.assertEqual(verify_puzzle(3, pieces, max_steps=1)['status'], 'NO_WIN_WITHIN_LIMIT')
        self.assertEqual(verify_puzzle(3, pieces, max_steps=2)['steps'], 2)

    def test_saved_exact_policy_works_without_running_a_search(self):
        state = self.position()
        first = get_exact_defender_reply(state, 5)
        policy = json.loads(json.dumps(first['defender_policy']))
        with patch('puzzle_logic.verify_puzzle') as search:
            cached = get_exact_defender_reply(state, 5, policy, time_budget=0)
        search.assert_not_called()
        self.assertEqual(cached['move'], first['move'])
        self.assertEqual(cached['status'], 'PROVEN')

    def test_creation_time_policy_survives_saving_and_loading(self):
        pieces = [(2, 0, 0, 'H'), (0, 0, 1, 'H')]
        proof = verify_puzzle(3, pieces, max_steps=3)
        scenario = PuzzleScenario.from_dict(dict(
            id='proof', board_size=3, pieces=pieces, s_optimal=proof['steps'],
            verification_status='VERIFIED', verification_key=proof['position_key'],
            defender_policy=json.loads(json.dumps(proof['defender_policy']))))
        scenario = PuzzleScenario.from_dict(json.loads(json.dumps(scenario.to_dict())))
        state = scenario.create_initial_state()
        make_puzzle_move(state, (2, 0), (1, 1))
        with patch('puzzle_logic.verify_puzzle') as search:
            reply = get_exact_defender_reply(state, 5, scenario.defender_policy, time_budget=0)
        search.assert_not_called()
        self.assertEqual(reply['status'], 'PROVEN')

    def test_timeout_never_returns_a_heuristic_or_random_reply(self):
        state = self.position()
        reply = get_exact_defender_reply(state, 5, time_budget=0)
        self.assertEqual(reply['status'], 'UNVERIFIED')
        self.assertIsNone(reply['move'])
        self.assertTrue(reply['telemetry'].timed_out)
        self.assertEqual(reply['telemetry'].completed_depth, 0)

    def test_short_horizon_failure_policy_is_not_reused_as_a_global_proof(self):
        state = self.position()
        pieces = [(0, 1, 0, 'H'), (1, 2, 1, 'H')]
        policy = {puzzle_position_key(3, pieces): dict(
            move=((1, 2), (0, 2)), steps=None, remaining=1)}
        reply = get_exact_defender_reply(state, 5, policy, time_budget=0)
        self.assertEqual(reply['status'], 'UNVERIFIED')
        self.assertIsNone(reply['move'])

    def test_defender_takes_a_proven_immediate_win(self):
        state = GameState(3, custom_setup=True)
        state.board[0][1] = Piece(0, 'A')
        state.board[1][1] = Piece(1, 'H')
        state.current_turn = 1
        reply = get_exact_defender_reply(state, 5, time_budget=0)
        self.assertEqual(reply['status'], 'PROVEN')
        child = state.clone()
        make_puzzle_move(child, *reply['move'])
        self.assertEqual(child.winner, 1)

    def test_canceled_analysis_returns_no_move(self):
        canceled = threading.Event()
        canceled.set()
        reply = get_exact_defender_reply(self.position(), 5, cancel_event=canceled)
        self.assertEqual(reply['status'], 'UNVERIFIED')
        self.assertIsNone(reply['move'])


class TestExactReplyIntegration(unittest.TestCase):
    def view(self):
        view = object.__new__(PuzzleGameView)
        view.is_game_active = True
        view.session = SimpleNamespace(is_neutralized=False, s_max=8, current_attempt_steps=1)
        view.scenario = SimpleNamespace(defender_policy={})
        view.config = {'agent_model': 'exact_defender'}
        view.state = TestExactDefender().position()
        view.ai_timer_id = None
        view._defender_queue = None
        view._defender_cancel = None
        view._defender_poll_id = None
        view.btn_ai_retry = Mock()
        view.lbl_status = Mock()
        view.lbl_delay = Mock()
        view.after = Mock(return_value='poll')
        view.after_cancel = Mock()
        view._apply_defender_move = Mock()
        return view

    @patch('views.puzzle_game_view.get_defender_move')
    @patch('views.puzzle_game_view.threading.Thread')
    def test_default_exact_path_does_not_call_depth_limited_engine(self, worker, heuristic):
        view = self.view()
        view._trigger_ai_move()
        worker.return_value.start.assert_called_once()
        heuristic.assert_not_called()
        view._defender_queue.put(dict(status='UNVERIFIED'))
        view._poll_defender_reply()
        view._apply_defender_move.assert_not_called()
        view.btn_ai_retry.grid.assert_called_once()

    def test_proven_reply_is_applied_and_its_policy_is_reused(self):
        view = self.view()
        view._defender_queue = Queue()
        entry = dict(move=((1, 2), (0, 2)), steps=2, remaining=5)
        view._defender_queue.put(dict(status='PROVEN', move=entry['move'],
                                     eval_score=99998, telemetry=SearchTelemetry(),
                                     proof_horizon=2, defender_policy={'key': entry}))
        view._poll_defender_reply()
        self.assertEqual(view.scenario.defender_policy['key'], entry)
        self.assertEqual(view._apply_defender_move.call_args.args[0], entry['move'])

    def test_cancel_discards_the_old_queue_before_late_result_arrives(self):
        view = self.view()
        old_queue = Queue()
        view._defender_queue = old_queue
        canceled = threading.Event()
        view._defender_cancel = canceled
        view._defender_poll_id = 'old-poll'
        view._cancel_defender_analysis()
        old_queue.put(dict(status='PROVEN'))
        view._poll_defender_reply()
        self.assertTrue(canceled.is_set())
        view.after_cancel.assert_called_once_with('old-poll')
        view._apply_defender_move.assert_not_called()


if __name__ == '__main__':
    unittest.main()
