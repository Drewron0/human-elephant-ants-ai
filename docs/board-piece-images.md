# Board piece images — 2026-11-04

## Problem
Boards display H, E and A letters instead of the three supplied character images.

## Success criteria
Human uses assets/orang.png, Elephant uses assets/gajah.png and Ant uses assets/semut.png. Images stay proportional and readable when boards resize, and player colors still identify ownership.

## Scope
Replace piece letters on gameplay boards, the stage editor board and stage thumbnails. Keep notation, rules text, game logic and saved stages unchanged.

## Constraints
Reuse the supplied PNGs without modifying them. Retain player-colored piece backgrounds and existing interactions. Share image loading and sizing across board renderers; use Pillow if necessary for transparent cropping and smooth resizing.

## Plan
Add shared image loading and size caching, replace the board letter drawing with centered images, then check image mapping, both owners, resizing and board interactions. Commit the completed change. Rollback is reverting that commit.

## Open questions
None. Awaiting implementation sign-off required by the Felix engineering skill.
