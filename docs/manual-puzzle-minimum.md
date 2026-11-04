# Author-entered puzzle minimum — 2026-11-04

## Problem
The user wants to specify the minimum step count directly instead of calculating or verifying it automatically.

## Success criteria
The editor has a required positive-integer Minimum Steps input, prefilled when editing an existing stage. Saving/loading preserves that value exactly and never launches a search. No verification button, worker, proof prerequisite or verified-minimum claim remains in the authoring/play flow.

## Scope
Remove the editor verification feature, accept stored minimums without requiring a proof, update catalog/game labels and tests. Keep the existing three-times-minimum move limit and counted undo. AI move selection and benchmark analysis remain separate and cannot redefine the author-entered count.

## Constraints
No new dependencies, menus, layout replacements or bulk saved-data rewrites. New stages have no guessed default minimum. Preserve basic input/board validation and prevent typing numbers in text fields from changing the board tool.

## Plan
Replace verification with an input and inline validation; persist manual provenance; remove play gating on proof metadata; update documentation; test manual save/edit/load, invalid input and the rendered editor. Commit a reversible checkpoint.

## Open questions
None. This explicitly replaces automatic minimum-step calculation.

## Validation
All 61 tests pass. Hidden Tk checks confirm there is no Verify button, a new minimum starts blank, invalid input is rejected inline, typing numbers does not change the placement tool, and manually saving six steps stays six across catalog/play/edit/load (move limit 18). Verification and static path search were patched to fail during that complete UI flow and were never called. Existing stage files are not rewritten automatically; authors edit their saved counts explicitly.
