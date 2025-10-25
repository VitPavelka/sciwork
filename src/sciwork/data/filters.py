# src/sciwork/data/filters.py

"""File discovery and loading helpers for data sets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple, TYPE_CHECKING

from ..imports import pandas as pd  # type: ignore
from ..logutil import get_logger
from .base import _DataHandlerBase
from .config import FilterSetConfig

LOG = get_logger(__name__)

if TYPE_CHECKING:  # pragma no cover - for static analysis only
	from ..fs.load import Load


class _FilterAndLoadMixin(_DataHandlerBase):
	"""Augment the base handler with file filtering and loading utilities."""

	# --- Helpers ---
	@staticmethod
	def _gather_files(folder: Path, patterns: Iterable[str]) -> List[Path]:
		files: List[Path] = []
		for pattern in patterns:
			files.extend(sorted(folder.glob(pattern)))
		unique = list(dict.fromkeys(files))
		return [path for path in unique if path.is_file()]

	@staticmethod
	def _filename_matches(name: str, keywords: Sequence[str], antikeywords: Sequence[str]) -> bool:
		lowered = name.lower()
		kw_pass = all(kw.lower() in lowered for kw in keywords) if keywords else True
		akw_pass = not any(akw.lower() in lowered for akw in antikeywords) if antikeywords else True
		return kw_pass and akw_pass

	@staticmethod
	def _merge_tokens(primary: Sequence[str], secondary: Sequence[str]) -> Tuple[str, ...]:
		ordered: List[str] = []
		for bucket in (primary, secondary):
			for token in bucket:
				if token and token not in ordered:
					ordered.append(token)
		return tuple(ordered)

	def _ensure_loader(self) -> "Load":
		loader = self._path_loader
		if loader is None:
			from ..fs.load import Load

			loader = Load(base_dir=self.config.data_folderpath)
			self._path_loader = loader
		return loader

	def _load_single_file(self, path: Path, set_config: FilterSetConfig) -> Any:
		loader = self._ensure_loader()
		loaded = loader.any_data_loader(
			path,
			sheet_name=set_config.sheet_name,
			header=set_config.header_row,
		)
		if isinstance(loaded, pd.DataFrame):
			LOG.debug("Loaded %s via any_data_loader with shape %s", path, loaded.shape)
		else:
			LOG.debug("Loaded %s via any_data_loader with type %s", path, type(loaded))
		return loaded

	# --------
	def filter_datafiles(self, patterns: Sequence[str] | None = None) -> None:
		"""
		Populate ``filtered_files`` and ``filtered_filenames`` per dataset.

		:param patterns: Optional glob patterns that are used to locate candidate files.
			When omitted, every file directly under ``data_folderpath`` is considered.
		:raises FileNotFoundError: If no files matching the provided patterns are found
			in the configured directory.
		"""

		folder = self.config.data_folderpath
		if patterns is None:
			patterns = ["*"]

		all_files = self._gather_files(folder, patterns)
		if not all_files:
			raise FileNotFoundError(f"No files found in {folder}")

		self.filtered_files = {}
		self.filtered_filenames = {}

		for set_config in self.config.iter_sets():
			effective_kw = self._merge_tokens(
				self.config.general_keywords, set_config.keywords
			)
			effective_akw = self._merge_tokens(
				self.config.general_antikeywords, set_config.antikeywords
			)

			matched: List[Path] = []
			for file in all_files:
				name = file.name.lower()
				if self._filename_matches(name, effective_kw, effective_akw):
					matched.append(file)

			key = self._set_key(set_config)
			self.filtered_files[key] = matched
			self.filtered_filenames[key] = [path.name for path in matched]
			LOG.debug("Filtered %d files for %s", len(matched), key)

	def data_loader(self) -> None:
		"""
		Load filtered files into adequate data structures.

		Notes
		-----
		File parsing is delegated to :meth:`sciwork.fs.load.Load.any_data_loader`
		so the handler benefits from the same classification logic that Sciwork
		already uses for CSV, Excel, JSON, XML, SIF, and other structured data
		sources.
		"""
		if not self.filtered_files:
			self.filter_datafiles()

		for set_config in self.config.iter_sets():
			key = self._set_key(set_config)
			files = self.filtered_files.get(key, [])
			frames = [self._load_single_file(path, set_config) for path in files]
			if not frames:
				LOG.warning("No data loaded for %s", key)
			self._register_dataset(set_config, frames)
