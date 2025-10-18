# src/sciwork/fs/pathops.py

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ..logutil import get_logger

from .base import PathLike
from .paths import Paths
from .dirs import Dirs
from .create import Create
from .delete import Delete
from .transfer import Transfer
from .getcontents import GetContents
from .open import Open
from .select import Select
from .load import Load
from .trees import TreeOps
from .archives import Archives

LOG = get_logger(__name__)


class PathOps(Paths, Dirs, Create, Delete, Transfer, GetContents, Open, Select, Load, TreeOps, Archives):
	"""
	One-stop helper combining path utilities, listing, selection, transfers, deletion,
	loading, archiving and simple OS openers.

	Examples
	--------
	>>> fs = PathOps.from_cwd()
	>>> p = fs.resolve_path("data", "file.csv")
	>>> choice = fs.select_paths("data", path_type="files")
	"""

	def __init__(
			self,
			base_dir: Optional[PathLike] = None,
			*,
			dry_run: bool = False,
			input_func: Optional[Callable[[str], str]] = None,
	) -> None:
		Paths.__init__(
			self,
			base_dir=base_dir or Path.cwd(),
			dry_run=dry_run,
			input_func=(input_func or input)
		)

	def __repr__(self) -> str:
		return f"PathOps(base_dir={self.base_dir!r}, dry_run={self.dry_run}, input_func={self.input_func})"
