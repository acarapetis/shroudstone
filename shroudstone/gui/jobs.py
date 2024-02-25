"""Simple framework for running asynchronous jobs in a Tk app in threads."""

from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, List, NamedTuple


class FutureContinuation(NamedTuple):
    """A future (representing a job running in a thread pool) along with a
    callback that will be executed in the main thread when the future
    completes. The callback is passed a single argument: the result value of
    the future."""
    future: Future
    continuation: Callable[[Any], None]


class TkWithJobs(tk.Tk):
    jobs: JobManager
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jobs = JobManager(self)


class JobManager:
    """Integrates a threadpool with a Tk widget, checking the list of futures for
    completed results every 50ms."""
    jobs: List[FutureContinuation]
    pool: ThreadPoolExecutor
    root: tk.Tk
    _timer_id: str

    def __init__(self, tk):
        self.jobs = []
        self.pool = ThreadPoolExecutor()
        self.root = tk
        self.tick()

    def tick(self):
        remaining: List[FutureContinuation] = []
        ready: List[FutureContinuation] = []
        for f in self.jobs:
            if f.future.done():
                ready.append(f)
            else:
                remaining.append(f)
        self.jobs = remaining
        for f in ready:
            f.continuation(f.future.result())
        self._timer_id = self.root.after(50, self.tick)

    def submit(self, func, callback, *args, **kwargs):
        future = self.pool.submit(func, *args, **kwargs)
        self.jobs.append(FutureContinuation(future, callback))

    def destroy(self):
        """Call this before destroying self.tk to avoid broken reference
        errors."""
        self.root.after_cancel(self._timer_id)
