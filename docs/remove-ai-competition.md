# Remove AI Competition — 2026-11-04

## Problem
The user did not request the four-minute AI Competition feature and explicitly requested its removal.

## Success criteria
Remove the menu entry, route, timer, standings, scoring APIs and feature-specific tests. Existing game modes and tests continue to work.

## Scope
Remove competition code and documentation. Preserve AI search, practice modes, benchmarks and saved user data. No unrelated feature changes.

## Constraints
Use the existing standard-library stack and retain ordinary puzzle controls and navigation.

## Plan
Remove entry points and dedicated modules, simplify shared puzzle/storage code, update documentation, then run tests and a hidden Tk navigation smoke check. A focused git commit provides a rollback point.

## Open questions
None. The user's request explicitly authorizes removal.

## Validation
All 43 remaining unit tests pass. A hidden Tk smoke check builds the remaining menu/configuration/puzzle/editor/benchmark/leaderboard/tutorial screens, executes a player move and AI reply, checks undo/reset, and returns through stage selection to the menu. No Python references to the removed feature remain; `git diff --check` passes.
