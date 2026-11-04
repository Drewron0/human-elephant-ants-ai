"""Run slow work off the UI thread and deliver results through Tk's event loop."""

import gc
import logging
import threading
import tkinter as tk
from collections.abc import Callable
from queue import Empty, Queue
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

Reporter = Callable[[Any], None]
Work = Callable[[threading.Event, Reporter], Any]
DONE = "done"
FAILED = "failed"
PROGRESS = "progress"


class BackgroundTask:
    """One cancellable worker; only the polling callback ever touches Tk widgets."""

    def __init__(
        self,
        widget: tk.Misc,
        work: Work,
        on_done: Callable[[Any], None],
        on_error: Callable[[str], None],
        on_progress: Callable[[Any], None] | None = None,
    ) -> None:
        self.widget = widget
        self.work = work
        self.on_done = on_done
        self.on_error = on_error
        self.on_progress = on_progress
        self.cancel_event = threading.Event()
        self._queue: Queue[tuple[str, Any]] = Queue()
        self._poll_id: str | None = None

    def start(self) -> None:
        """Start the worker, first freeing Tk garbage here so the worker never has to."""
        gc.collect()
        threading.Thread(target=self._run, daemon=True).start()
        self._poll_id = self.widget.after(settings.AI_POLL_INTERVAL_MS, self._poll)

    def cancel(self) -> None:
        """Ask the worker to stop and discard anything it still produces."""
        self.cancel_event.set()
        if self._poll_id is not None:
            self.widget.after_cancel(self._poll_id)
            self._poll_id = None

    def _run(self) -> None:
        try:
            result = self.work(self.cancel_event, lambda item: self._queue.put((PROGRESS, item)))
        except Exception as error:
            logger.exception("Background task failed")
            self._queue.put((FAILED, str(error)))
        else:
            self._queue.put((DONE, result))

    def _poll(self) -> None:
        self._poll_id = None
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except Empty:
                break
            if kind == PROGRESS:
                if self.on_progress:
                    self.on_progress(payload)
            elif kind == DONE:
                self.on_done(payload)
                return
            else:
                self.on_error(payload)
                return
        self._poll_id = self.widget.after(settings.AI_POLL_INTERVAL_MS, self._poll)
