# src/sciwork/fs/create.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..logutil import get_logger
from .base import PathOpsBase, PathLike

LOG = get_logger(__name__)

__all__ = ["Create"]


class Create(PathOpsBase):
	"""
	Creation helpers: folders, files, temp dirs, parents.
	Expects `PathOpsBase` fields+helpers: base_dir, dry_run, _abs(...).
	"""
	# --- Interclass Helper ---
	def ensure_parent(self, path: PathLike, *, mode: int = 0o777) -> Path:
		"""
		Ensure the parent directory of a file path exists.

		Resolves ``path`` relative to ``base_dir`` (if not absolute) and ensures
		that ``path.parent`` exists (creating it if needed). Honors ``dry_run``.

		:param path: File path whose parent directory will be ensured.
		:param mode: Permission bits for newly created directories (ignored on Windows).
		:return: Resolved the absolute parent directory path.
		"""
		parent = self._abs(path).parent
		self.make_folder(parent, exist_ok=True, mode=mode)
		return parent.resolve()

	# --- Files ---
	def touch_file(
			self,
			path: PathLike,
			*,
			create_parents: bool = True,
			exist_ok: bool = True,
			mode: Optional[int] = None
	) -> Path:
		"""
		Create a file if it does not exist or update its modification time.

		Respects ``base_dir`` and ``dry_run``. When ``create_parents`` is True,
		missing parent directories are created.

		:param path: File path (absolute or relative to ``base_dir``).
		:param create_parents: If True, ensure parent directories exist.
		:param exist_ok: If False and file exist, raise class:`FileExistsError`.
		:param mode: Optional permission bits to apply after creation/update.
		:return: Resolved the absolute file path.
		:raises IsADirectoryError: When the path is not a file.
		:raises FileExistsError: When the file exists and ``exist_ok`` is False.
		:raises PermissionError: When permission is denied.
		:raises OSError: Other OS-level errors.
		"""
		target = self.coerce_file_path(path)

		if target.exists():
			if not target.is_file():
				msg = f"Path exists and is not a file: {target}"
				LOG.error(msg)
				raise IsADirectoryError(msg)  # or NotAFileError in future Python
			if not exist_ok:
				msg = f"File already exists: {target}"
				LOG.error(msg)
				raise FileExistsError(msg)
			if self.dry_run:
				LOG.info("[dry-run] touch (update mtime): %s", target)
				return target.resolve()
			target.touch(exist_ok=True)
			if mode is not None:
				try:
					target.chmod(mode)
				except Exception as exc:
					LOG.warning("Failed to apply mode %o to %s: %s", mode, target, exc)
			LOG.info("Touched file: %s", target)
			return target.resolve()

		# not exists
		if create_parents:
			self.ensure_parent(target)

		if self.dry_run:
			LOG.info("[dry-run] create file: %s", target)
			return target.resolve()

		try:
			target.touch(exist_ok=True)
			if mode is not None:
				try:
					target.chmod(mode)
				except Exception as exc:
					LOG.warning("Failed to apply mode %o to %s: %s", mode, target, exc)
			LOG.info("Created file: %s", target)
			return target.resolve()
		except PermissionError:
			LOG.exception("Permission denied while touching file: %s", target)
			raise
		except OSError as exc:
			LOG.exception("OS error while touching file '%s': %s", target, exc)
			raise

	def create_file(
			self,
			path: PathLike,
			*,
			op: str = "a",
			create_parents: bool = True,
			permissions: Optional[int] = None,
			encoding: str = "utf-8"
	) -> Path:
		"""
		Create an empty file using the given open mode.

		Modes:
			-``'a'``: creation if missing, open for appending (do not truncate if exists).
			- ``'w'``: creation or truncate to zero lengths.
			- ``'x'``: exclusive creation; fail if the file already exists.

		Respects ``base_dir`` and ``dry_run``.

		:param path: File path (absolute or relative to ``base_dir``).
		:param op: One of {'a', 'w', 'x'}.
		:param create_parents: If True, ensure the parent directory exists first.
		:param permissions: Optional permission bits to apply after creation/update.
		:param encoding: Text encoding that is used when creating the file handle.
		:return: Resolved the absolute file path.
		:raises ValueError: Invalid operation.
		:raises FileExistsError: With ``op='x'`` when the file exists.
		:raises PermissionError: When permission is denied.
		:raises OSError: Other OS-level errors.
		"""
		if op not in {"a", "w", "x"}:
			raise ValueError(f"Invalid op: {op}. Expected 'a', 'w', or 'x'.")

		target: Path = self.coerce_file_path(path)

		if create_parents:
			self.ensure_parent(target)

		if self.dry_run:
			LOG.info("[dry-run] create file (%s): %s", op, target)
			return target.resolve()

		try:
			# create / truncate, according to mode; we don't write content
			with open(target, op, encoding=encoding):
				pass
		except PermissionError:
			LOG.exception("Permission denied while creating file (%s): %s:", op, target)
			raise
		except OSError as exc:
			LOG.exception("OS error while creating file '%s' (%s): %s", target, op, exc)
			raise

		self._apply_mode(target, permissions)

		LOG.info("Created file (%s): %s", op, target)
		return target.resolve()

	# --- Folders ---
	def make_folder(
			self,
			path: PathLike,
			*,
			exist_ok: bool = True,
			mode: int = 0o777,
	) -> Path:
		"""
		Create a directory (and parents) at *path*.

		The path is resolved relative to ``self.base_dir`` if it is not absolute.
		Honors ``dry_run``: when True, the action is only logged and no filesystem
		changes are performed.

		:param path: Target directory path (absolute or relative to ``base_dir``).
		:param exist_ok: If True, do not raise if the directory already exists.
						If False, raise: class:`FileExistsError` when it exists.
		:param mode: Permission bits for newly created directories (ignored on Windows).
		:return: Resolved an absolute path to the directory (existing or created).
		:raises NotADirectoryError: When a non-directory exists at the given path.
		:raises FileExistsError: When the directory exists and ``exist_ok`` is False.
		:raises PermissionError: When permission is denied.
		:raises OSError: For other OS-level errors.
		"""
		target = self._abs(path)

		if target.exists():
			if not target.is_dir():
				msg = f"Path exists and is not a directory: {target}"
				LOG.error(msg)
				raise NotADirectoryError(msg)
			if exist_ok:
				LOG.info("Directory already exists: %s", target)
				return target.resolve()
			msg = f"Directory already exists: {target}"
			LOG.error(msg)
			raise FileExistsError(msg)

		if self.dry_run:
			LOG.info("[dry-run] mkdir -p %s", target)
			return target.resolve()

		try:
			Path(target).mkdir(parents=True, exist_ok=True, mode=mode)
			LOG.info("Created directory: %s", target)
			return target.resolve()
		except PermissionError:
			LOG.exception("Permission denied while creating directory: %s", target)
			raise
		except OSError as exc:
			LOG.exception("OS error while creating directory '%s': %s", target, exc)
			raise
