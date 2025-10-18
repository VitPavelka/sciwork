# src/sciwork/fs/getcontents.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .base import PathLike, PathOpsBase
from ..logutil import get_logger
from .filters import matches_filters, coerce_time_cutoff
from .inspect import build_metadata, extract_exif

LOG = get_logger(__name__)

try:
	from .dirs import Dirs
except ImportError:
	LOG.error(f"GetContents class requires the optional dependency 'sciwork.fs.Dirs' to work.")
	raise

__all__ = ["GetContents"]


class GetContents(PathOpsBase):
	"""
	Handles directory listing and filtering of files and folders based
	on various criteria.

	This class provides two main APIs: ``self.get_files_or_folders`` for
	getting files and folders as separate lists or getting directory
	contents with detailed metadata by ``self.get_contents``.
	It supports filters like pattern matching, time-based cutoffs,
	and optionally includes EXIF metadata for files.
	"""
	# --- Helpers ---
	@staticmethod
	def _time_cutoff_pair(
			older_than: Optional[Union[float, int, str, datetime]],
			newer_than: Optional[Union[float, int, str, datetime]],
	) -> tuple[Optional[float], Optional[float]]:
		"""Turn older/newer specs into POSIX timestamps (or None)."""
		return coerce_time_cutoff(older_than), coerce_time_cutoff(newer_than)

	@staticmethod
	def _try_exif(entry: Path) -> Optional[Dict[str, Any]]:
		"""Attach best-effort EXIF (lazy import) for files."""
		try:
			return extract_exif(entry, file_metadata=False)
		except Exception as exc:
			LOG.debug("EXIF unavailable for %s: %s", entry, exc)
			return None

	def _confirm_threshold_once(self, *, threshold: int, root: Path) -> bool:
		"""
		Ask the user for confirmation when the listing grows past a threshold.
	    Uses `sciwork.console.Prompter.confirm()` for a consistent UX.
		"""
		ask = self._pick_prompt(None, confirm=True)
		msg = f"Listing has exceeded {threshold} items in '{root}'. Continue?"
		return ask(msg)

	# --- Shared iterator for both APIs ---
	@staticmethod
	def __iter_matching_entries(
			root: Path,
			*,
			recursive: bool,
			follow_symlinks: bool,
			include_hidden: bool,
			pattern: Optional[str],
			antipattern: Optional[str],
			shell_pattern: Optional[str],
			cutoff_older: Optional[float],
			cutoff_newer: Optional[float],
			ignore_errors: bool = True,
	):
		"""
		Yield (entry, stat_result) for items under *root* that pass name+time filters.
		Uses lstat() to keep symlink semantics consistent with metadata.
		For parameters, see :meth:`get_contents`.
		"""
		it = (root.rglob("*") if recursive else root.iterdir())
		if recursive and not follow_symlinks:
			it = (p for p in it if not (p.is_dir() and p.is_symlink()))

		for entry in it:
			name = entry.name
			if not matches_filters(
					name, include_hidden=include_hidden,
					pattern=pattern, antipattern=antipattern, shell_pattern=shell_pattern
			):
				continue
			try:
				st = entry.lstat()
				mtime = float(st.st_mtime)
				if cutoff_older is not None and mtime < cutoff_older:
					continue
				if cutoff_newer is not None and mtime > cutoff_newer:
					continue
			except PermissionError as exc:
				if ignore_errors:
					LOG.warning("Permission denied while stat() '%s': %s", entry, exc)
					continue
				raise

			yield entry, st

	# --- Public API ---
	def get_files_and_folders(
			self,
			folder_path: Optional[PathLike] = None,
			*,
			recursive: bool = False,
			include_hidden: bool = True,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			follow_symlinks: bool = False,
			return_absolute_paths: bool = False,
			max_items: Optional[int] = None,
			older_than: Optional[Union[float, int, str, datetime]] = None,
			newer_than: Optional[Union[float, int, str, datetime]] = None
	) -> Dict[str, list[Path]] | None:
		"""
		Return two lists ``(files, folders)`` with paths matching the filters.

		The method mirrors the filtering knobs of :meth:`get_contents` but
		collects *only* paths (no metadata), which is both faster and simpler
		to consume when you just need the file/directory lists.

		:param folder_path: Folder to list.
							If ``None``, the inspected folder is set to ``self.base_dir``.
		:param recursive: Recurse into subdirectories.
		:param include_hidden: If False, skip dot-entries.
		:param pattern: Include only names containing this substring.
		:param antipattern: Exclude names containing this substring.
		:param shell_pattern: Shell-like pattern for names (e.g., ``"*.jpg"``).
		:param follow_symlinks: If True, follow directory symlinks during recursion.
		:param return_absolute_paths: If True, keys are absolute paths; otherwise,
									  keys are relative to *folder*.
		:param max_items: Stop after collecting this many items.
		:param older_than: Only include entries **older** that this cutoff (mtime).
						   Accepts seconds-ago (number), ISO 8601 string, duration
						   like '2h', '7d', or a class `datetime.datetime`.
		:param newer_than: Only include entries **newer** that this cutoff (mtime).
						   Same accepted formats as ``older_than``.
		:return:
		"""
		inspected = folder_path if folder_path else self.base_dir
		dirs = Dirs(inspected)

		if dirs.is_folder_empty(folder_path):
			LOG.info("Folder %s is empty", folder_path)
			return {"files": [], "folders": []}

		root = dirs.try_get_dir(folder_path)

		cutoff_older, cutoff_newer = self._time_cutoff_pair(older_than, newer_than)

		files: list[Path] = []
		folders: list[Path] = []

		for entry, _st in self.__iter_matching_entries(
				root, recursive=recursive, follow_symlinks=follow_symlinks,
				include_hidden=include_hidden, pattern=pattern, antipattern=antipattern,
				shell_pattern=shell_pattern, cutoff_older=cutoff_older, cutoff_newer=cutoff_newer,
				ignore_errors=True
		):
			key = entry.resolve() if return_absolute_paths else entry.relative_to(root)
			(folders if entry.is_dir() else files).append(key)

			if max_items is not None and len(files) + len(folders) >= max_items:
				LOG.info("Hit max_items=%d; stopping listing in %s", max_items, root)
				break

		LOG.info("Collected %d files and %d folders from: %s", len(files), len(folders), root)
		return {"files": files, "folders": folders}

	def get_contents(
			self,
			folder_path: Optional[PathLike] = None,
			*,
			recursive: bool = False,
			include_hidden: bool = True,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			follow_symlinks: bool = False,
			exif: bool = False,
			max_items: Optional[int] = None,
			confirm_if_over: Optional[int] = None,
			ignore_errors: bool = True,
			return_absolute_paths: bool = False,
			older_than: Optional[Union[float, int, str, datetime]] = None,
			newer_than: Optional[Union[float, int, str, datetime]] = None
	) -> Dict[str, Dict[str, Any]]:
		"""
		List directory contents and return a mapping of *path* → metadata.

		Metadata per entry includes:
			- ``type``: 'file' | 'dir' | 'symlink'
			- ``size`` (bytes, files only)
			- ``created`` / ``modified`` / ``accessed`` (ISO 8601, UTC)
			- ``mime`` (best-effort via :mod:`mimetypes`)
			- ``ext`` (file  extension, lowercase, including dot)
			- optional ``exif`` (if ``exif=True`` and Pillow is available)

		:param folder_path: Folder to list.
							If ``None``, the inspected folder is set to ``self.base_dir``.
		:param recursive: Recurse into subdirectories.
		:param include_hidden: If False, skip dot-entries.
		:param pattern: Include only names containing this substring.
		:param antipattern: Exclude names containing this substring.
		:param shell_pattern: Shell-like pattern for names (e.g., ``"*.jpg"``).
		:param follow_symlinks: If True, follow directory symlinks during recursion.
		:param exif: If True, try to attach a small EXIF dict for images (best-effort).
		:param max_items: Stop after collecting this many items.
		:param confirm_if_over: If set (e.g., 500), prompt once via ``sciwork.console.Prompter``
								when the number of the result meets/exceeds this threshold.
								Abort listing in the user declines.
		:param ignore_errors: If True, log and continue on errors; else re-raise.
		:param return_absolute_paths: If True, keys are absolute paths; otherwise,
									  keys are relative to *folder*.
		:param older_than: Only include entries **older** that this cutoff (mtime).
						   Accepts seconds-ago (number), ISO 8601 string, duration
						   like '2h', '7d', or a class `datetime.datetime`.
		:param newer_than: Only include entries **newer** that this cutoff (mtime).
						   Same accepted formats as ``older_than``.
		:return: Dict[path_str, dict] mapping to metadata.
		:raises FileNotFoundError: If *folder* does not exist.
		:raises NotADirectoryError: If the path is not a directory.
		"""
		inspected = folder_path if folder_path else self.base_dir
		dirs = Dirs(inspected)

		if dirs.is_folder_empty(folder_path):
			LOG.info("Folder %s is empty", folder_path)
			return {}

		root = dirs.try_get_dir(folder_path)

		cutoff_older, cutoff_newer = self._time_cutoff_pair(older_than, newer_than)

		result: Dict[str, Dict[str, Any]] = {}
		stop_listing = False
		confirmed = (confirm_if_over is None)  # if a threshold not set, we're implicitly confirmed

		def _add(entry: Path, sst) -> None:
			nonlocal result, stop_listing, confirmed
			if stop_listing:
				return
			info = build_metadata(entry, st=sst)
			if exif and info.get("type") == "file":
				ex = self._try_exif(entry)
				if ex:
					info["exif"] = ex
			key = str(entry if return_absolute_paths else entry.relative_to(root))
			result[key] = info

			# threshold confirmation (once)
			if not confirmed and confirm_if_over is not None and len(result) >= confirm_if_over:
				if not self._confirm_threshold_once(threshold=confirm_if_over, root=root):
					LOG.warning("User declined listing beyond %d items in %s", confirm_if_over, root)
					stop_listing = True
					return
				LOG.info("User confirmed listing beyond %d items in %s", confirm_if_over, root)
				confirmed = True

		for e, st in self.__iter_matching_entries(
				root, recursive=recursive, follow_symlinks=follow_symlinks,
				include_hidden=include_hidden, pattern=pattern, antipattern=antipattern,
				shell_pattern=shell_pattern, cutoff_older=cutoff_older, cutoff_newer=cutoff_newer,
				ignore_errors=ignore_errors
		):
			if stop_listing:
				break
			_add(e, st)
			if stop_listing:
				break
			if max_items is not None and len(result) >= max_items:
				LOG.info("Hit max_items=%d; stopping listing in %s", max_items, root)
				break

		LOG.info("Listed %d entr%s from: %s", len(result), "y" if len(result) == 1 else "ies", root)
		return result
