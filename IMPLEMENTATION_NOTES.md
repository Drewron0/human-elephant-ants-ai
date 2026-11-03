# Proposal gaps — 2026-11-04

Approved scope: preserve the existing application and standard-library stack;
repair search, baseline fairness, puzzle verification and benchmark validity.
No GUI redesign or general-purpose architecture rewrite.

Success criteria: reproducible random 10-step puzzle corpus; 1,000 games per
model/player combination; all 12 combinations; genuine shortest-path player;
cutoff-only pruning statistics; finite legal timeout fallback and completed
search depth; bounded verification never labels an unknown result as proven.

Verification is an offline task. Exact global defense on arbitrary boards
within two seconds is not promised. The full 12,000-game experiment is a
separate command; development uses small runs and focused regression tests.

Plan: search and telemetry, bounded verification and puzzle data, benchmark
integration and documentation. Changes remain in the current checkout and
are committed at each working checkpoint so they can be reverted separately.

Decisions: benchmark generation uses certified sparse 11x11 races, whose
geometric lower bound and forced-win strategy prove exactly 10 moves. The
legacy tactical layouts are preserved, but their bad stored routes are removed
and their old counts are explicitly unverified. Unknown verification never
falls back to a stationary-opponent search. Player and defender random streams
are separate; all combinations share a corpus and seed.

Search checkpoint: iterative deepening, exception-safe board restoration,
completed depth, timeout flags, purely random baseline, and cutoff-only metrics.
Integration checks include the greedy-route regression and all 12 combinations
in a one-game CLI smoke run. Full 12,000-game results are intentionally separate.

Final validation: 43 tests pass, including the actual 1,000-iteration simulator
loop with immediate failed attempts. The CLI smoke completes all 12 model/player
combinations; report readback verifies a shared corpus hash, finite scores and
zero baseline pruning. Hidden Tk checks build the benchmark controls, insert a
real result row, and build the puzzle board with telemetry. Five generated
10-step puzzles pass the standalone verifier. Existing profile data is untouched;
storage tests run in a temporary working directory.
