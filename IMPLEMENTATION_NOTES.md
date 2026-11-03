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
