"""
SciWork — scientific workflows' toolkit.

Top-level API keeps imports lazy:

    from sciwork import PathOps
    fs = PathOps()

    from sciwork import Console, Prompter  # both lazy
    con = Console()
    p = Prompter("message")

    from sciwork import RobustConfig
    rc = RobustConfig()

    # imports toolbox stays under its own namespace
    from sciwork import imports
    df = imports.pandas.read_csv("file.csv")
"""

from importlib import import_module
from importlib.metadata import version, PackageNotFoundError as _PNF
from typing import TYPE_CHECKING

try:
	__version__ = version("sciwork")
except _PNF:
	__version__ = "0.0.0+local"

__all__ = [
	"__version__",
	# main facades
	"PathOps",
	"Console", "Prompter", "Printer",
	"RobustConfig", "configure_logging",
	# namespaces
	"imports", "config", "console", "logutil", "fs", "stats", "plot",
	# optional fs convenience (lazy)
	"Paths", "Dirs", "Create", "Delete", "Transfer", "Open",
	"Archives", "Select", "GetContents", "Load", "TreeOps",
	# stats convenience (lazy)
	"MathStat", "normal_round", "moving_average",
	# plotting convenience (lazy)
	"Plot",
]

# --- lazy maps ---------------------------------------------------------------
_CONSOLE_EXPORTS = {"Console", "Prompter", "Printer"}

_FS_EXPORTS = {
	"PathOps", "Paths", "Dirs", "Create", "Delete", "Transfer", "Open",
	"Archives", "Select", "GetContents", "Loaders", "TreeOps",
}

_STATS_EXPORTS = {"MathStat", "normal_round", "moving_average"}
_PLOT_EXPORTS = {"Plot"}


def __getattr__(name: str):
	# --- main facades ---
	if name == "PathOps":
		return import_module("sciwork.fs").PathOps
	if name == "Console":
		return import_module("sciwork.console").Console
	if name == "Prompter":
		return import_module("sciwork.console").Prompter
	if name == "Printer":
		return import_module("sciwork.console").Printer
	if name == "RobustConfig":
		return import_module("sciwork.config").RobustConfig
	if name == "configure_logging":
		return import_module("sciwork.logutil").configure_logging

	# --- namespaces (lazy) ---
	if name == "imports":
		return import_module("sciwork.imports")
	if name == "config":
		return import_module("sciwork.config")
	if name == "console":
		return import_module("sciwork.console")
	if name == "logutil":
		return import_module("sciwork.logutil")
	if name == "fs":
		return import_module("sciwork.fs")
	if name == "stats":
		return import_module("sciwork.stats")
	if name == "plot":
		return import_module("sciwork.plot")

	# --- lazy re-exports from console/fs packages ---
	if name in _CONSOLE_EXPORTS:
		return getattr(import_module("sciwork.console"), name)
	if name in _FS_EXPORTS:
		return getattr(import_module("sciwork.fs"), name)
	if name in _STATS_EXPORTS:
		return getattr(import_module("sciwork.stats"), name)
	if name in _PLOT_EXPORTS:
		return getattr(import_module("sciwork.plot"), name)

	raise AttributeError(f"module 'sciwork' has no attribute {name!r}")


# Help type-checkers without eager imports
if TYPE_CHECKING:
	from . import imports, console, logutil, fs, plot  # noqa: F401
	from .logutil import configure_logging  # noqa: F401
	from .config import RobustConfig  # noqa: F401
	from .console import Printer, Console, Prompter  # noqa: F401
	from .fs import (
		PathOps, Paths, Dirs, Create, Delete, Transfer, Open,
		Archives, Select, GetContents, Load, TreeOps,  # noqa: F401
	)
	from .stats import MathStat, normal_round, moving_average  # noqa: F401
	from .plot import Plot  # noqa: F401
