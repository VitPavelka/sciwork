# src/sciwork/data/base.py

"""Base infrastructure for :mod:`sciwork.data` handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, TYPE_CHECKING

from ..imports import pandas as pd  # type: ignore
from ..logutil import get_logger
from .config import DataHandlerConfig, FilterSetConfig

LOG = get_logger(__name__)

if TYPE_CHECKING:  # pragma no cover - only for type checkers
	from ..fs.load import Load


@dataclass(frozen=True)
class DataSet:
	"""Container representing a named collection of data frames."""

	name: str
	frames: List[pd.DataFrame]


class _DataHandlerBase:
	"""Provide configuration handling and dataset bookkeeping."""

	def __init__(self, config: DataHandlerConfig) -> None:
		self.config = config
		self.filtered_files: Dict[str, List[Path]] = {}
		self.filtered_filenames: Dict[str, List[str]] = {}
		self.data_sets: Dict[str, List[pd.DataFrame]] = {}
		self._path_loader: Optional["Load"] = None
		self._validate_root()

	# -----------------------------------------------------
	def _validate_root(self) -> None:
		"""Ensure the configured data folder exists."""

		if not self.config.data_folderpath.exists():
			raise FileNotFoundError(
				f"Data folder does not exist: {self.config.data_folderpath}"
			)

	# -----------------------------------------------------
	@staticmethod
	def _set_key(set_config: FilterSetConfig) -> str:
		return set_config.name

	def _resolve_set_numbers(self, set_numbers: Optional[Sequence[int]]) -> List[str]:
		"""Return dataset keys for ``set_numbers`` or all loaded sets."""

		if set_numbers is None:
			return list(self.data_sets.keys())
		return [f"Set {num}" for num in set_numbers]

	def _register_dataset(self, set_config: FilterSetConfig, frames: Sequence[pd.DataFrame]) -> None:
		self.data_sets[self._set_key(set_config)] = list(frames)

	def get_dataset(self, set_number: int) -> DataSet:
		"""Return a dataset by numeric identifier."""

		key = f"Set {set_number}"
		frames = self.data_sets.get(key)
		if frames is None:
			raise KeyError(f"Dataset {set_number} has not been loaded.")
		return DataSet(name=key, frames=frames)

	# -----------------------------------------------------
	@staticmethod
	def _iter_files(folder: Path, patterns: Iterable[str]) -> Iterable[Path]:
		for pattern in patterns:
			yield from folder.glob(pattern)
