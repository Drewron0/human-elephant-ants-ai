# Random Challenge background generation

Date: 2026-10-27  
Status: Approved and implemented.

## 1. Problem

Random Challenge currently generates three puzzles on Tkinter's main thread.
The loading message appears first, but generation still prevents the window
from processing clicks and repainting normally. Windows may report the app as
not responding.

Users need to navigate normally while challenges are being generated. Clicking
the tab repeatedly must not start more generation jobs.

## 2. Success criteria

- Selecting Random Challenge immediately shows `Creating Random Challenge.....`.
- Generation runs outside the main thread. The window continues processing
  events while generation is running.
- Users can switch tabs, change settings, or leave the puzzle selection screen.
  Buttons are not disabled across the screen.
- At most one Random Challenge generation job runs in the application at a time.
- Returning to Random Challenge shows the existing job's loading state or its
  completed results, without generating another batch.
- A completed batch contains the same three challenge configurations as today.
- Completion never changes the user's active tab or overwrites another screen.
- Play Stage is unavailable while the active Random Challenge tab has no ready
  challenge. It must not silently launch a previously selected or default stage.
- Generation errors produce a readable message rather than leaving an endless
  loading state. Selecting Random Challenge again permits one retry.
- Leaving the screen or closing the application causes no callbacks to update
  destroyed widgets and does not make the application wait for the worker.

## 3. Scope

Included:

- One background worker thread that generates the three puzzles sequentially.
- A thread-safe result queue carrying either a completed batch or an error.
- Main-thread polling using Tkinter's `after()`, approximately every 100 ms.
- Small application-owned job state and a cache of the completed batch, kept
  until the application closes. This survives leaving and reopening the screen.
- Loading, success, and failure handling within the existing Random Challenge
  tab. Errors or results arriving on another tab do not force navigation or
  interrupt the user with a popup.
- Clearing stale stage details and guarding Play Stage during random loading.
- Focused automated tests and a short manual responsiveness check.

Excluded:

- Solver changes, faster generation, or stronger winnability guarantees.
- Processes, worker pools, new dependencies, progress percentages, or new
  refresh/cancel buttons.
- Changes to stage verification, benchmarks, networking, or saved data formats.
- Persisting generated challenges between application launches.

## 4. Constraints

- Reuse `generate_winnable_puzzle()` with the existing 6x6 configurations:
  move ranges 5-7, 6-8, and 7-10.
- The worker only calculates puzzles and writes to its queue. It never reads
  widget values, modifies widgets, or calls Tkinter methods, including `after()`.
- Only the main thread owns UI updates and the shared loading/result state.
  Queue reads must be non-blocking; do not use `join()` or sleeps on the UI thread.
- Cancel screen-owned polling callbacks when that screen is destroyed. Let the
  worker finish independently; a new selection screen can collect its result.
- Use a daemon worker so closing the application does not wait for generation.
- Keep this explainable as one producer, one queue, and one main-thread consumer.
- Threads improve responsiveness but do not guarantee faster CPU-heavy Python
  calculations. Remaining slowdown is a limitation to measure, not a reason to
  add multiprocessing to this change.

## 5. Plan

1. Add minimal application-owned state for one job, its queue, and its result.
   Keep the idle/loading/ready/failed states simple; no new service framework.
2. Change the random-tab path to show loading and start or reuse the worker,
   returning control to Tkinter immediately. Reuse the existing card rendering
   for completed results instead of duplicating it.
3. Poll the queue on the main thread. Cache completed results regardless of the
   current tab, but refresh the display only when Random Challenge is active.
   On failure, clear the running state and allow a user-triggered retry.
4. Guard Play Stage while random results are unavailable, preserve navigation,
   and clean up polling when leaving the screen.
5. Update `tests/test_puzzle_select.py` with controlled workers/results. Verify
   loading before completion, tab switching, one-job reuse, cached results after
   reopening the screen, correct card rendering, failure/retry, guarded Play,
   and cleanup without updates to destroyed widgets.
6. Manually navigate between tabs during real generation and close the screen
   while work is pending. Record whether the UI continues to process events.

Expected implementation files: `gui.py`, `views/puzzle_select_view.py`, and
`tests/test_puzzle_select.py`. No generator changes are planned.

Risk: a CPU-heavy worker can still slow the application. Also, an active worker
continues using CPU after the user leaves the screen; keeping one job per app
prevents repeated navigation from multiplying that work.

Rollback: revert the implementation commit to restore the current synchronous
generation and loading message. No user data migration is involved.

## 6. Open questions

None. Proposed defaults are one batch per application session, navigation
available during generation, and retry by selecting Random Challenge again
after a failure.

Implementation checkpoint (2026-10-27):

- Added one daemon worker, queue polling, application-session caching, and a
  loading guard for Play Stage. No new dependencies or generator changes.
- Passed 10 Random Challenge tests and 3 stage-editor regression tests.
- In a live check with the real generator, switched to Custom Stages, left for
  the main menu, reopened the selector, and displayed the completed three-card
  batch. Navigation remained responsive.
- The user stopped Computer Use before the close-during-generation check.
  That manual shutdown check remains unverified; cleanup is covered by tests.
- Remaining limit: generation continues consuming CPU in the background.
