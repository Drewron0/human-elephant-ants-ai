# Custom-only puzzle menu

1. Problem: the puzzle menu mixes user-created stages with built-in presets and
   random challenges. Only user-created stages should be listed and played here.
2. Success: the menu shows saved custom stages, supports create/edit/delete/play,
   and shows a useful empty state when none exist. No preset or random fallback.
3. Scope: remove preset data, category tabs, random-menu workers/cache/polling and
   their obsolete tests; update the game launch, verifier and documentation.
4. Constraints: preserve custom stage data, editor verification and benchmark
   generation, which remains an independently used evaluation feature.
5. Plan: simplify the catalog and selector, remove unused app state and game
   fallbacks, update callers/tests, then verify the custom create-to-play flow.
   Commit the scoped change after tests pass.
6. Open questions: none. The user explicitly requested the custom-only menu and
   removal of unused code from the removed preset/random features.

Validation: all 51 tests pass. Hidden Tk checks cover an empty catalog, creating
and verifying a custom stage, saving it, editing it, playing a move, and deleting
the last stage. Production-source searches find no preset catalog, random-menu
worker/cache/polling or category filtering left. The generic random-challenge
generator and its unused retry option were removed; the benchmark now generates
its required 10-step corpus directly, preserving its seeded position sequence.
