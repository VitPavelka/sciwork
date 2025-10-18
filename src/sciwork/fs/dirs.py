# src/sciwork/fs/dirs.py

from __future__ import annotations

import time
import tempfile
from contextlib import contextmanager

from pathlib import Path
from typing import Optional, Generator, Any

from ..logutil import get_logger
from .base import PathOpsBase, PathLike
from .filters import matches_filters, iter_dir_filtered

LOG = get_logger(__name__)

__all__ = ["Dirs"]


class Dirs(PathOpsBase):
	"""
	Directory-centric helpers built on top of :class:`~sciwork.fs.base.PathOpsBase`.

	Provides quick checks for emptiness and a simple polling utility to wait
	until a directory contains at least one matching entry.
	"""

	# --- Validation / Resolution ---
	def require_dir(self, p: PathLike, *, create: bool = False) -> Path:
		"""
		Ensure *p* exists and is a directory; optionally create it.

		:param p: Directory path (absolute or relative).
		:param create: If ``True`` and the directory does not exist, it will be created.
						Respects :attr:`dry_run`.
		:return: Resolved an absolute directory path.
		:raises NotADirectoryError: When the path exists and is not a directory.
		:raises FileNotFoundError: When the directory does not exist and ``create=False``.
		"""
		target = self._abs(p)
		if target.exists():
			if not target.is_dir():
				raise NotADirectoryError(f"Path exists and is not a directory: {target}")
			return target.resolve()

		if create:
			from .create import Create
			return Create().make_folder(target, exist_ok=True)

		raise FileNotFoundError(f"Directory not found: {target}")

	def try_get_dir(self, folder_path: PathLike, *, missing_ok: bool = False) -> Optional[Path]:
		"""
		Resolve *folder_path* relative to :attr:`base_dir`, ensure it is a directory,
		and return the resolved :class:`pathlib.Path`.

		:param folder_path: Target folder (absolute or relative to ``base_dir``).
		:param missing_ok: If ``True``, return ``None`` when the path does not exist;
						   otherwise, raise :class:`FileNotFoundError`.
		:return: Resolved directory path, or ``None`` when missing and ``missing_ok=True``.
		:raises FileNotFoundError: When missing and ``missing_ok`` is ``False``.
		:raises NotADirectoryError: Whe the path exists but is not a directory.
		"""
		raw = str(folder_path).strip() if isinstance(folder_path, PathLike) else ""
		if raw in {"", ".", "./", ".\\"}:
			root = self.base_dir
		else:
			root = self._abs(raw)

		if not root.exists() and raw and raw == self.base_dir.name and self.base_dir.exists():
			root = self.base_dir

		if not root.exists():
			if missing_ok:
				LOG.warning("Directory not found (missing_ok=True): %s", root)
				return None
			raise FileNotFoundError(f"Directory does not exist: {root}")
		if not root.is_dir():
			raise NotADirectoryError(f"Path exists but is not a directory: {root}")
		return root.resolve()

	# --- Queries ---
	def is_folder_empty(
			self,
			folder_path: Optional[PathLike] = None,
			*,
			include_hidden: bool = True,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			files_only: bool = False
	) -> bool:
		"""
		Return ``True`` if the folder contains **no entries** passing the filters.

		If no filters are provided, all direct children are considered.
		Scanning is non-recursive.

		:param folder_path: Directory to inspect (absolute or relative to ``base_dir``).
							If ``None``, the :attr:`base_dir` is used.
		:param include_hidden: If ``False``, ignore entries whose *name* starts with ``.``.
		:param pattern: Include only entries whose *name* contains this substring.
		:param antipattern: Exclude entries whose *name* contains this substring.
		:param shell_pattern: Shell-like pattern matched against the *name* (e.g., ``"*.csv"``). Applied in addition to ``pattern`` filters.
		:param files_only: If True, consider files only (no subdirectories).
		:return: True when no entries match the filters; False otherwise.
		:raises FileNotFoundError: Folder does not exist.
		:raises NotADirectoryError: Path exists but is not a directory.
		"""
		inspected = folder_path if folder_path else self.base_dir
		root = self.try_get_dir(inspected)
		assert root is not None  # try_get_dir raises when missing_ok=False

		# Fast path: return on first match
		for entry in root.iterdir():
			if files_only and not entry.is_file():
				continue
			if matches_filters(
					entry.name,
					include_hidden=include_hidden,
					pattern=pattern,
					antipattern=antipattern,
					shell_pattern=shell_pattern
			):
				LOG.info("Folder %s is not empty", root)
				return False
		LOG.info("Folder %s is empty", root)
		return True

	def wait_until_not_empty(
			self,
			folder_path: Optional[PathLike] = None,
			*,
			timeout: float = 30.0,
			poll_interval: float = 0.5,
			include_hidden: bool = True,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			files_only: bool = False,
	) -> int:
		"""
		Poll a folder until at least one entry matches the filters.

		:param folder_path: Folder to watch.
							If ``None``, the :attr:`base_dir` is used.
		:param timeout:  Maximum time to wait in seconds. Use 0 for a single check.
		:param poll_interval: Delay between checks in seconds.
		:param include_hidden: If False, ignore dot-files.
		:param pattern: Include only names containing this substring.
		:param antipattern: Exclude names containing this substring.
		:param shell_pattern: Shell-like pattern for names (e.g., "*.csv").
		:param files_only: If True, consider files only (no subdirectories).
		:return: Number of matching entries when the condition is met (> 0).
		:raises FileNotFoundError: Folder does not exist.
		:raises NotADirectoryError: Path exists but is not a directory.
		:raises TimeoutError: If the folder stays empty past *timeout*.
		"""
		inspected = folder_path if folder_path else self.base_dir
		root = self.try_get_dir(inspected)
		assert root is not None

		deadline = time.monotonic() + max(0.0, timeout)

		while True:
			try:
				# count (stop early on first match for speed)
				count = 0
				for _ in iter_dir_filtered(
						root,
						include_hidden=include_hidden,
						pattern=pattern,
						antipattern=antipattern,
						shell_pattern=shell_pattern,
						files_only=files_only
				):
					count += 1
					if count > 0:
						LOG.info("Folder became non-empty (%d match%s): %s",
						         count, "" if count == 1 else "es", root)
						return count
			except PermissionError as exc:
				LOG.warning("Permission issue while scanning %s: %s", root, exc)

			if time.monotonic() >= deadline:
				raise TimeoutError(f"Timeout waiting for folder '{root}' to become non-empty.")
			time.sleep(max(0.05, poll_interval))

	# --- Temporary directories ---
	@contextmanager
	def temp_dir(
			self,
			folder_path: Optional[PathLike] = None, *,
			prefix: str = "sciwork-",
			suffix: str = "",
			cleanup: bool = True
	) -> Generator[Path, Any, None]:
		"""
		Create a temporary directory and yield its path.

		In :attr:`dry_run` mode, a hypothetical path is yielded and no filesystem
		changes are performed. When ``cleanup`` is True, the directory is removed
		on context exit; otherwise, it is kept on disk.

		Usage
		-----
		with self.temp_dir() as td:
			# do some stuff with td

		:param folder_path: Parent directory for the temp directory.
		:param prefix: Prefix for the temp directory name.
		:param suffix: Suffix for the temp directory name.
		:param cleanup: Remove the directory when leaving the context.
		:yields: :class:`pathlib.Path` pointing to the (real or hypothetical) temporary directory.
		"""
		temp_parent = self.try_get_dir(folder_path) or self.base_dir
		if self.dry_run:
			hypothetical = (temp_parent / f"{prefix}XXXXXX{suffix}").resolve()
			LOG.info("[dry-run] would create temp dir: %s", hypothetical)
			try:
				yield hypothetical
			finally:
				LOG.info("[dry-run] would %s temp dir: %s", "remove" if cleanup else "keep", hypothetical)
			return

		if cleanup:
			td = tempfile.TemporaryDirectory(prefix=prefix, suffix=suffix, dir=temp_parent)
			path = Path(td.name).resolve()
			LOG.info("Created temp dir: %s", path)
			try:
				yield path
			finally:
				LOG.info("Removing temp dir: %s", path)
				td.cleanup()
		else:
			path = Path(tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=temp_parent)).resolve()
			LOG.info("Created temp dir: %s", path)
			try:
				yield path
			finally:
				LOG.info("Keeping temp dir (no cleanup): %s", path)
