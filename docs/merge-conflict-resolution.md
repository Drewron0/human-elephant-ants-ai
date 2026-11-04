# Resolve puzzle branch merge — 2026-11-04

## Problem
The current merge has conflicts in puzzle logic, stage selection and the stage editor.

## Success criteria
No unmerged index entries or conflict markers remain. The merged application retains only custom stages, manual minimum-step input and working defender interfaces. Tests and relevant UI flows pass, and the merge is committed.

## Scope
Resolve the active merge and integration issues only. Preserve user data, unrelated changes and both parents' history.

## Constraints
Use the current checkout and standard-library stack. Do not abort/reset the merge or push remotely.

## Plan
Inspect both parents, resolve manual-entry/API conflicts, retain the custom-only catalog, verify the merged code, stage exact files and finish the merge commit. The merge parents provide rollback history.

## Open questions
None. Felix clarified that only custom stages should remain. The five preset layouts remain available in the parent commit history.

Validation: all 61 tests passed. A hidden Tk smoke check exercised the empty catalog, create/save/play/edit flow and manual minimum persistence while verification helpers were guarded against invocation. The repository scan found no conflict markers.
