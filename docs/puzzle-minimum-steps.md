# Calculate puzzle minimum steps — 2026-11-04

Historical scope: superseded by `custom-stage-verification.md`. The latest requirement checks moving defenders at creation time, rather than using a stationary route as a winning proof.

## Problem
Preset and older custom stages display stored step targets that were not calculated from their piece positions.

## Success criteria
Calculate the shortest legal piece route to the target from each starting board; use its length for the displayed minimum, delay baseline and move limit. Reconstruct a legal route and report no route instead of substituting six steps.

## Scope
The user explicitly chose stationary enemies for this calculation. Reuse BFS for each player piece through the starting board, respecting friendly blockers and cyclic capture rules, then choose the shortest route. Update preset/custom stage loading, editor verification and puzzle labels. Actual AI turns remain enabled; adversarial benchmark verification stays separate.

## Constraints
No new dependencies, menus, board layouts or saved-data rewrites. A stationary route is not a guarantee against moving defenders.

## Plan
Reuse the existing BFS entry point, calculate scenario targets on load, update affected UI/editor text and add path replay/blocker regressions. Run the existing suite and hidden Tk checks, then commit the focused change for rollback.

## Open questions
None. The user confirmed stationary enemies and requested continuation.

## Validation
All 50 unit tests pass, including blocked-square detours, cyclic captures, shortest-piece selection, replay of every preset route, stale saved counts and no-route handling. Hidden Tk checks confirm calculated counts on stage selection and all 12 puzzle screens, plus editor verification and reset/back navigation. Adversarial verifier and benchmark regressions remain passing.
