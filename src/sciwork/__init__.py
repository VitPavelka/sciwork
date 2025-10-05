"""
SciWork - scientific workflows' toolkit.

Top-level API keeps import lazy:
	from sciwork import RobustConfig
	rc = RobustConfig()
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
	# convenience re-exports (lazy via __getattr__)
	"RobustConfig",
	"KeySpec",
	"make_choices_validator",
	"bootstrap_json_file",
	"DEFAULT_PROJECT_SCHEMA",
	# namespaces
	"config",
	"logutil",
	"configure_logging"
]


def __getattr__(name: str):
	# convenience symbols from sciwork.config
	if name in {
		"RobustConfig",
		"KeySpec",
		"make_choices_validator",
		"bootstrap_json_file",
		"DEFAULT_PROJECT_SCHEMA"
	}:
		mod = import_module("sciwork.config")
		return getattr(mod, name)

	# expose subpackages as namespaces
	if name == "config":
		return import_module("sciwork.config")
	if name == "logutil":
		return import_module("sciwork.logutil")
	if name == "configure_logging":
		return import_module("sciwork.logutil").configure_logging

	raise AttributeError(f"module 'sciwork' has no attribute {name!r}")


# Help type-checkers without eager imports
if TYPE_CHECKING:
	from .config import (
		RobustConfig,
		KeySpec,
		make_choices_validator,
		bootstrap_json_file,
		DEFAULT_PROJECT_SCHEMA
	)
	from . import logutil  # noqa: F401
	from .logutil import configure_logging
