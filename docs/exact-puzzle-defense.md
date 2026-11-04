# Use proven defensive replies in puzzle play — 2026-11-04

## Problem
Stage verification establishes a best-defense winning distance, but live puzzle play uses a separate depth-limited heuristic. The supplied five-piece position is verified at eight player moves, yet weak live replies permit earlier wins.

## Success criteria
The default puzzle defender uses proven optimal replies under the puzzle's move limit. Persist reusable defensive decisions from stage verification. Resolve positions absent from the saved policy with the same exact solver, in the background. Never substitute a heuristic/random reply when exact analysis is incomplete. Undo/reset/navigation must discard pending replies. Reproduce the supplied position and prevent a shorter-than-eight win against the corrected defender.

## Scope
Puzzle verification policy, exact live defender, background integration, model labels and focused regressions. Preserve research baseline models and benchmark behavior. Existing verified stages can be analyzed lazily without rewriting user data.

## Constraints
Standard library only. Finite-distance proofs are exact; a failure proof is usable only within its proven remaining-move horizon. Keep the 120-second/3,000,000-node budget, report incomplete analysis visibly, and allow retry/undo/reset. No weaker fallback.

## Plan
Export complete cached defensive decisions from the verifier, support exact defender-turn analysis, persist the policy, and make puzzle play consume it. Add cancellation/stale-result guards and regression tests for saved/live replies, winning player mistakes, incomplete search and undo. Run the suite plus the supplied-position simulation and UI checks, then commit a reversible checkpoint.

## Open questions
None. Exact defense becomes the default puzzle choice; deliberately weaker research baselines remain explicit options.

## Validation
All 62 tests pass. The supplied five-piece position is played to a win in eight player moves against exact defensive replies; a separate tuple-based AND/OR checker proves the chosen first reply rules out seven total player moves while eight remains achievable. Tests cover saved-policy reuse, horizon-limited failure certificates, immediate defensive wins, canceled/timed-out searches and refusal to guess. Hidden Tk checks exercise the exact default, saved replies, counted undo, incomplete-analysis pause and cancellation of late replies after reset. Cache serialization round trips and the seeded benchmark corpus remain unchanged when no defensive policy is present.

The first uncached reply on the supplied position took about 39 seconds; later replies reused proofs in under a millisecond. New stage verification saves reusable decisions. Existing stages remain compatible and can populate their policy in memory or be re-verified/saved. A position that cannot be solved within the live budget pauses instead of weakening the defender.
