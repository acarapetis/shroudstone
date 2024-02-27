"""Simple framework for running asynchronous jobs in a Tk app in threads."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, List
from typing_extensions import Generic, ParamSpec, TypeVar


class TkWithJobs(tk.Tk):
    jobs: JobManager

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jobs = JobManager(self)

    def debounce(self, timeout: int = 500):
        """Use this Tk's event loop to debounce a 0-arg function.

        Useful for preventing on-change/on-keypress event handlers from firing too often."""
        state: dict = {"timer": None}

        def decorator(func):
            def clear_timer_and_run(*_):
                state["timer"] = None
                func()

            def start_timer(*_):
                if state["timer"] is not None:
                    self.after_cancel(state["timer"])
                state["timer"] = self.after(timeout, clear_timer_and_run)

            return start_timer

        return decorator


T = TypeVar("T")
P = ParamSpec("P")


@dataclass(frozen=True)
class FutureContinuation(Generic[T]):
    """A future (representing a job running in a thread pool) along with a
    callback that will be executed in the main thread when the future
    completes. The callback should be passed a single argument: the result
    value of the future."""

    future: Future[T]
    continuation: Callable[[T], None]


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

    def submit(
        self,
        func: Callable[P, T],
        callback: Callable[[T], None],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        future = self.pool.submit(func, *args, **kwargs)
        self.jobs.append(FutureContinuation(future, callback))

    def destroy(self):
        """Call this before destroying self.tk to avoid broken reference
        errors."""
        self.root.after_cancel(self._timer_id)
