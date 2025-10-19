# src/sciwork/fs/transfer.py

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from ..logutil import get_logger
from .base import PathLike, PathOpsBase

LOG = get_logger(__name__)

__all__ = ["Transfer"]


class Transfer(PathOpsBase):
	"""
	File/dir transfer utilities (copy/move/delete).

	This class reuses:
		- :class:`PathOpsBase` for path resolution and dry-run flags
		- :class:`Create` for :meth:`ensure_parent`
		- :class:`Deleter` for removing existing targets (when overwrite=True)

		Parameters mirror shutil semantics but add safety rails and consistent logging.
	"""
	# --- Helpers ---
	@staticmethod
	def _resolve_transfer_target(src: Path, dst: Path) -> Path:
		"""
		Compute the effective target path for a transfer.

		If *dst* exists and is a directory, returns ``dst / src.name``.
		Otherwise, returns *dst* as-is.

		:param src: Source path (must exist).
		:param dst: Destination path (can be a dir or file path).
		:return: Effective target path.
		"""
		return (dst / src.name) if (dst.exists() and dst.is_dir()) else dst

	def _preflight_target(
			self,
			target: Path,
			*,
			overwrite: bool,
			create_parents: bool
	) -> None:
		"""
		Ensure parent, and optionally remove existing *target* if overwrite=True.
		Respects ``dry_run``.

		:param target: The target path to create or overwrite.
		:param overwrite: If True and the target exist, remove it.
		:param create_parents: Ensure the parent directory exists.
		"""
		if create_parents:
			try:
				from .create import Create
			except Exception:
				LOG.error("Transfer class requires the optional dependency 'sciwork.fs.Create' to work.")
				raise
			Create().ensure_parent(target)

		if target.exists() and overwrite:
			if self.dry_run:
				LOG.info("[dry-run] remove existing target: %s", target)
				return
			# Remove file/symlink or directory tree
			if target.is_dir():
				try:
					from .delete import Delete
				except Exception:
					LOG.error("Transfer class requires the optional dependency 'sciwork.fs.Delete' to work.")
					raise
				Delete().delete(target, recursive=True, missing_ok=True)
			else:
				try:
					target.unlink()
				except FileNotFoundError:
					pass  # race-safe

	# --- Copy / Move primitives ---
	@staticmethod
	def _copy_file(
			src: Path,
			dst: Path,
			*,
			preserve_metadata: bool,
			follow_symlinks: bool
	) -> None:
		"""Copy a single file with desired semantics."""
		if preserve_metadata:
			shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
		else:
			shutil.copy(src, dst, follow_symlinks=follow_symlinks)

	@staticmethod
	def _copy_dir(
			src: Path,
			dst: Path,
			*,
			preserve_metadata: bool,
	) -> None:
		"""
		Copy a directory tree.

		We use the copytree with dirs_exist_ok=True (target already removed if overwrite).
		The copy function is copy2 when *preserve_metadata*; else copy.
		"""
		copy_func = shutil.copy2 if preserve_metadata else shutil.copy
		shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=copy_func)

	@staticmethod
	def _move_any(src: Path, dst: Path) -> None:
		"""Cross-device save move."""
		shutil.move(str(src), str(dst))

	def prepare_transfer(
			self,
			source: Path,
			destination: Path,
			*,
			overwrite: bool,
			create_parents: bool
	):
		"""
		Prepare file transfer by validating the source and destination paths,
		handling target preparation, and resolving conflicts such as existing
		files based on the `overwrite` policy.

		:param source: Path object representing the source file or directory.
		:param destination: Path object representing the destination file or directory.
		:param overwrite: Boolean indicating whether to overwrite existing target files.
		:param create_parents: A boolean indicating whether to create non-existent parent
		    directories for the destination path.
		:return: A tuple containing the absolute path of the source and the resolved
		    target destination path.
		"""
		src = self._abs(source)
		if not src.exists():
			raise FileNotFoundError(f"Source path '{src}' does not exist.")

		dst_in = self._abs(destination)
		target = self._resolve_transfer_target(src, dst_in)

		# refuse clobbering when overwrite=False
		if target.exists() and not overwrite:
			raise FileExistsError(f"Target path '{target}' exists (use overwrite=True).")

		# prep target (parents and optionally clear)
		self._preflight_target(target, overwrite=overwrite, create_parents=create_parents)

		return src, target

	# --- Public API ---
	def transfer(
			self,
			source: PathLike,
			destination: PathLike,
			*,
			operation: Literal["copy", "move"] = "copy",
			overwrite: bool = False,
			preserve_metadata: bool = True,
			create_parents: bool = True,
			follow_symlinks: bool = True
	) -> Path:
		"""
		Copy or move a file/directory.

		Behavior
		--------
		* If *destination* is an existing **directory**, the entry is copied/moved *into* it.
		* If *destination* looks like a file path, the entry is copied/moved **to that path**.
		* When ``overwrite=True``, an existing target is removed first (file/symlink or whole tree).
		* ``move`` uses :func:`shutil.move` (cross-device).

		:param source: Source file or directory.
		:param destination: Destination directory of the final path.
		:param operation: ``"copy"`` (default) or ``"move"``.
		:param overwrite: Remove the existing *target* first (default: False).
		:param preserve_metadata: For file copies, use :func:`shutil.copy2` (default: True).
								  For directory trees, the copytree uses ``copy2`` when True.
		:param create_parents: Ensure the parent directory for *target* exists (default: True).
		:param follow_symlinks: For **file copies**, pass through to shutil to follow symlinks (default: True).
		:return: The absolute resolved *target* path.
		:raises FileNotFoundError: Source does not exist.
		:raises FileExistsError: Target exists and the ``overwrite=False``.
		:raises ValueError: Invalid *operation*.
		:raises PermissionError: On OS-level errors.
		:raises OSError: On OS-level errors.
		"""
		src, target = self.prepare_transfer(
			source, destination,
			overwrite=overwrite, create_parents=create_parents
		)

		if self.dry_run:
			LOG.info("[dry-run] %s %s -> %s", operation, src, target)
			return target.resolve()

		try:
			if operation == "copy":
				if src.is_dir():
					self._copy_dir(src, target, preserve_metadata=preserve_metadata)
				else:
					self._copy_file(
						src, target,
						preserve_metadata=preserve_metadata,
						follow_symlinks=follow_symlinks
					)
			elif operation == "move":
				self._move_any(src, target)
			else:
				raise ValueError(f"Unsupported operation (must be 'copy' or 'move': {operation}")
		except PermissionError:
			LOG.exception("Permission denied during %s: %s -> %s", operation, src, target)
			raise
		except OSError as exc:
			LOG.exception("OS error during %s '%s' -> '%s': %s", operation, src, target, exc)
			raise

		LOG.info("%s OK: %s -> %s", operation.capitalize(), src, target)
		return target.resolve()
