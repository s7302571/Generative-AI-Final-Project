"""Sandboxed Python execution for the run_python tool.

Constraints:
- Whitelist of imports (pandas, numpy, math, matplotlib.pyplot, plotly)
- No network, no filesystem, no subprocess
- Hard timeout via SIGALRM (Unix only; this app targets macOS/Linux)
- A `fig` variable in the local scope is captured and returned to the UI

This is good enough for an academic project. It is NOT a security boundary —
do not expose this tool to untrusted users in production.
"""

from __future__ import annotations

import io
import signal
import sys
import threading
import traceback
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any

from . import config

ALLOWED_MODULES = {
    "math",
    "statistics",
    "pandas",
    "numpy",
    "matplotlib",
    "matplotlib.pyplot",
    "plotly",
    "plotly.graph_objects",
    "plotly.express",
}


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if name in ALLOWED_MODULES or root in {m.split(".")[0] for m in ALLOWED_MODULES}:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Import of '{name}' is not allowed in the sandbox")


# Build the safe builtins dict from the real builtins, dropping dangerous names.
_BUILTINS = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
_BLOCKED = {
    "open", "exec", "eval", "compile", "__import__",
    "input", "breakpoint", "exit", "quit", "help",
}
SAFE_BUILTINS = {k: v for k, v in _BUILTINS.items() if k not in _BLOCKED}
SAFE_BUILTINS["__import__"] = _restricted_import


@dataclass
class CodeResult:
    ok: bool
    stdout: str
    error: str | None
    figure: Any | None  # matplotlib Figure or plotly Figure, if produced


class _Timeout:
    """SIGALRM-based timeout. No-op when not running in the main thread —
    `signal.signal` is main-thread-only, and Streamlit runs each script in a
    worker thread, so we silently drop the timeout there. The eval CLI runs
    in the main thread and gets real enforcement.
    """

    def __init__(self, seconds: int):
        self.seconds = seconds
        self._installed = False

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            return
        def handler(signum, frame):
            raise TimeoutError(f"Code execution exceeded {self.seconds}s")
        self._prev = signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.seconds)
        self._installed = True

    def __exit__(self, *exc):
        if self._installed:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._prev)


def run_python(code: str) -> CodeResult:
    # Force matplotlib into a non-interactive backend to avoid display issues.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sandbox_globals = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__sandbox__",
    }

    # Pre-import common libs so the model doesn't have to
    sandbox_globals["plt"] = plt
    try:
        import pandas as pd
        import numpy as np
        sandbox_globals["pd"] = pd
        sandbox_globals["np"] = np
    except ImportError:
        pass
    try:
        import plotly.graph_objects as go
        sandbox_globals["go"] = go
    except ImportError:
        pass

    buf = io.StringIO()
    try:
        with _Timeout(config.CODE_TIMEOUT_SECONDS), redirect_stdout(buf):
            exec(compile(code, "<sandbox>", "exec"), sandbox_globals)
    except Exception:
        return CodeResult(
            ok=False,
            stdout=buf.getvalue(),
            error=traceback.format_exc(limit=3),
            figure=None,
        )

    fig = sandbox_globals.get("fig")
    # If the user used pyplot without assigning, grab the current figure if any
    if fig is None and plt.get_fignums():
        fig = plt.gcf()
    return CodeResult(ok=True, stdout=buf.getvalue(), error=None, figure=fig)


RUN_PYTHON_DESCRIPTION = (
    "Execute Python code in a sandbox to compute exact numerical answers or "
    "render visualizations. Available libs: pandas (pd), numpy (np), math, "
    "matplotlib.pyplot (plt), plotly.graph_objects (go). For charts, assign "
    "the figure to a variable named `fig`. For numbers, print() the result."
)

RUN_PYTHON_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute. Print numeric results; assign charts to `fig`.",
        }
    },
    "required": ["code"],
}
