# Light mode and capture legend

Approved by Felix on 2026-11-04.

## Problem
The desktop UI is dark and dense, and capture rules are hidden behind a guide.

## Success criteria
- Light appearance across screens, controls, tables and dialogs.
- A visible Legend in the menu, practice, puzzle play and guide.
- Human beats Ant, Ant beats Elephant, Elephant beats Human, matching `BEATS`.
- Readable labels, visible keyboard focus, quieter secondary actions.
- Existing navigation, boards, AI, editing and saved data continue to work.

## Scope
Shared theme and controls, menu composition, capture legend, affected view styles
and documentation. Game rules, search, persistence and dependencies are unchanged.

## Constraints
Keep Tkinter and supplied character PNGs. Check the supported 1050x720 minimum
and larger desktop windows. Native UI inspection replaces the web-only inspector.

## Plan
1. Update shared semantic light colors and control states.
2. Add a reusable legend derived from game rules; place it beside play and guide content.
3. Modernize the menu, remove hardcoded dark surfaces, and improve affected layouts.
4. Run unit tests and native visual/interaction checks; commit the scoped change.
Rollback is a revert of this UI commit; no stored data migration is required.

## Open questions
None. Felix approved using Ant beats Elephant for the third capture rule.

## Design notes
- Taste direction: Editorial greeting, seed 383967326; no redraws.
- Native adaptation: Segoe UI, pale gray ground, white surfaces, blue primary action.
- Identity: supplied Human, Elephant and Ant artwork in the capture legend.
- Menu question: where should I play? Practice/puzzle question: what can capture what?
- Before review: small controls and captions, strong black panel edges, equally
  weighted menu actions, dominant red Quit button, no persistent capture legend.
- Apple HIG findings: minor typography, control hierarchy and grouping issues;
  small targets are especially unsuitable for touch. Existing resizable boards,
  named actions and consistent system type are retained.
- No new sample data, external images, fonts or dependencies.
