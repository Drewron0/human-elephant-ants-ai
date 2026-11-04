# Simplified AI competition

1. Problem: direct PvP and network setup add options that the competition does
   not need. Players need comparable scores against the same AI.
2. Success: each scored attempt has a four-minute wall clock including AI turns;
   wins score max(0, 1000 - 10 * moves), losses/timeouts score zero; equal scores
   use completion time. Undo and reset are unavailable during competition.
3. Scope: add a fixed-challenge competition entry and standings using the existing
   puzzle board; remove direct PvP, its settings, callbacks and network.py. Keep
   AI practice, editor and benchmark tools. Existing stored data is preserved.
4. Constraints: standard library only, current UI components, small direct changes.
   Preserve pre-existing edits in ai_engine.py and views/tutorial_view.py.
5. Plan: implement scoring/clock/storage, connect the existing puzzle screen and
   competition setup, remove PvP/network dependencies, then verify timing edges,
   rankings, GUI startup and existing tests. Commit only this task's changes.
6. Open questions: none. The user's approval of the four-minute scoring rules and
   request to implement and remove networking authorize this scope. A player gets
   one attempt per challenge per round; clearing that round permits a new contest.

Validation: all 49 tests pass. A hidden Tk end-to-end game records a 10-move win
for Player A (900 points), times Player B out (zero), and verifies the standings.
Practice setup, practice records and the menu load with network.py absent. Clock
tests cover the exact 240-second boundary, late AI replies and leaving a match.
