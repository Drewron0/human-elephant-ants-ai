# Verify custom puzzles before saving — 2026-11-04

## Problem
Static BFS can report a route that a moving defender immediately defeats. The supplied 6x6 board has a six-move static route, but the Ant's first move a2-b3 permits Human c4xb3. Adversarial verification finds no forced win within six player moves.

## Success criteria
Verify each new or edited custom stage against every legal defensive reply before saving. Store the proven minimum and bind it to the checked board. Never substitute a static route or a guessed count when verification is inconclusive. Load the saved result without rerunning a search. A loss keeps undo/reset available, and successful undo actions remain counted.

## Scope
Reuse the existing bounded adversarial Minimax verifier for stage creation. Preserve layouts, AI models and benchmarks. Existing uncertified stages may remain practice layouts but must not display a proven minimum. No new menus or board redesign.

## Constraints
Standard library only. Exhausting a verification budget means unknown, not unwinnable. A completed negative result excludes wins only within the checked move horizon. Creation-time verification has a larger budget than the playing AI. Preserve saved user files unless the user saves an edit.

## Plan
Persist a board-bound verification result; replace the editor's static check; remove load-time BFS claims; update labels; keep terminal losses recoverable through counted undo. Add the supplied board and stale-result regressions, run the suite and hidden Tk checks, and commit the focused change for rollback.

## Open questions
None. The latest requirement is a winning strategy from the initial position against moving defenders, superseding the earlier stationary-enemy baseline.

## Larger verification budget — 2026-11-04
1. Problem: the 10-second/300,000-node creation budget ends too early for complex custom stages.
2. Success criteria: allow up to 120 seconds and 3,000,000 nodes before reporting an incomplete verification.
3. Scope: creation/editing verification budgets, progress text, documentation and the existing worker test. Preserve the 14-move horizon and in-game AI budgets.
4. Constraints: keep background execution and never turn an exhausted budget into a winning proof.
5. Plan: raise the two limits, update the existing test/documentation, run the suite and commit a reversible checkpoint. A full two-minute dense-board solve is not required to validate this configuration change.
6. Open questions: none; the user explicitly requested a larger timeout.

## Validation
All 58 tests pass. The supplied image is reconstructed in a regression test: static BFS reports six moves, Human c4xb3 refutes that route, and exhaustive bounded verification finds no forced win within six player moves. Hidden Tk checks save a proven stage asynchronously, reload its cached result without searching, keep the UI responsive during dense-board verification, reject its unverified minimum, and recover from a terminal capture through a counted undo. The dense board's true minimum remains unverified within the creation-time budget; no global unwinnability claim is made. Saved user data and layouts are preserved.
