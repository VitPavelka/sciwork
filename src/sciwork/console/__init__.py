# src/sciwork/console/__init__.py

"""
Console helpers: pretty printing, prompts, timers.
Re-exports (lazy at runtime, friendly to type checkers):

    from sciwork.console import Printer, Prompter, Console
"""

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["Printer", "Prompter", "Console", "base"]


def __getattr__(name: str):
    # Lazy, runtime re-exports
    if name == "Printer":
        return import_module("sciwork.console.printer").Printer
    if name == "Prompter":
        return import_module("sciwork.console.prompter").Prompter
    if name == "Console":
        return import_module("sciwork.console.console").Console
    if name == "base":
        return import_module("sciwork.console.base")
    raise AttributeError(f"module 'sciwork.console' has no attribute {name!r}")


# Help PyCharm / mypy without forcing eager imports
if TYPE_CHECKING:
    from .printer import Printer  # noqa: F401
    from .prompter import Prompter  # noqa: F401
    from .console import Console  # noqa: F401
    from . import base  # noqa: F401
