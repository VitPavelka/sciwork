# src/sciwork/fs/delete.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..logutil import get_logger
from .base import PathOpsBase, PathLike
from .filters import matches_filters, is_hidden_path
from ..imports import Send2Trash
from .delete_utils import (
	delete_file as _delete_file,
	delete_dir as _delete_dir,
	delete_symlink as _delete_symlink,
	iter_clear_candidates
)

LOG = get_logger(__name__)

__all__ = ["Delete"]


class Delete(PathOpsBase):
	"""
	Deletion utilities: remove files/dirs, move to trash, and clear folder contents.

	The class respects :attr:`dry_run` from :class:`~sciwork.fs.base.PathOpsBase` and
	uses :class:`~sciwork.console.Prompter` for interactive confirmations (when available).
	"""
	# --- Confirmation Helper ---
	def _confirm_removal(self, action: str) -> bool:
		"""
		Confirms the removal of a file by prompting the user with a confirmation message.

		:param action: The action is described in the confirmation message.
		:return: True if the user confirms the action, otherwise False.
		"""
		ask = self._pick_prompt(None, confirm=True)
		message = f"Are you sure you want to {action}?"
		return ask(message)

	# --- Single Target ---
	def delete(
			self,
			path: PathLike,
			*,
			missing_ok: bool = False,
			recursive: bool = False,
			follow_symlinks: bool = False,
			confirm: bool = False
	) -> None:
		"""
		Deletes a *path* (file, directory, or symlink).

		- Files and symlinks are unlinked.
		- Directories:
			* if ``recursive`` is True, remove the whole tree;
			* if False (default), only remove an empty directory (like ``rmdir``).
		- Symlinks to directories are treated as symlinks (unlinked) unless
			``follow_symlinks`` is True.

		Respects ``dry_run`` (only logs actions).

		:param path: Path of the target file or directory (absolute or relative to ``base_dir``).
		:param missing_ok: If True, do not raise when the path does not exist.
		:param recursive: When deleting a directory, remove contents recursively.
		:param follow_symlinks: If True, and *path* is a symlink to a directory,
								delete the target directory tree instead of the link.
		:param confirm: If True, prompt the user before deleting.
		:raises FileNotFoundError: When the path does not exist and ``missing_ok`` is False.
		:raises ValueError: Unsupported path type or path type.
		"""
		target = self._abs(path)

		if not target.exists():
			if missing_ok:
				LOG.warning("delete skipped (missing): %s", target)
				return
			raise FileNotFoundError(f"Path '{target}' not found.")

		if self.dry_run:
			kind = "symlink" if target.is_symlink() else ("dir" if target.is_dir() else "file")
			suffix = " (recursive)" if (kind == "dir" and recursive) else ""
			LOG.info(f"[dry-run] delete %s%s: %s", kind, suffix, target)
			return

		confirmation = self._confirm_removal(f"delete {target}") if confirm else True

		# Actual deletion
		try:
			if confirmation:
				# Symlinks (to files or dirs) - unlink by default
				if target.is_symlink() and not follow_symlinks:
					_delete_symlink(target, follow_symlinks=follow_symlinks)
					LOG.info("Deleted symlink: %s", target)
				elif target.is_file():
					_delete_file(target)
					LOG.info("Deleted file: %s", target)
				elif target.is_dir():
					_delete_dir(target, recursive=recursive)
					LOG.info("Deleted %s directory: %s: ", "recursive" if recursive else "empty", target)
				else:
					# Fallback - unusual filesystem entry
					raise ValueError(f"Unsupported path type: {target}")
			else:
				LOG.warning("The user has not confirmed the deletion of: %s", target)
				return
		except FileNotFoundError:
			if missing_ok:
				LOG.warning("delete skipped (disappeared): %s", target)
				return
			raise

	def trash(self, path: PathLike, *, missing_ok: bool = False, confirm: bool = False) -> None:
		"""
		Move a file or directory to the OS thrash/recycling bin.
		Requires the optional dependency ``Send2Trash``

		:param path: Target path (absolute or relative to ``base_dir``).
		:param missing_ok: If True, do not raise when the path does not exist.
		:param confirm: If True, prompt the user before moving to trash.
		:raises FileNotFoundError: When the path does not exist and ``missing_ok`` is False.
		"""
		target = self._abs(path)
		if not target.exists():
			if missing_ok:
				LOG.warning("thrash skipped (missing): %s", target)
				return
			raise FileNotFoundError(f"Path '{target}' not found.")

		if self.dry_run:
			LOG.info("[dry-run] move to thrash: %s", target)
			return

		confirmation = self._confirm_removal(f"move to thrash {target}") if confirm else True
		if confirmation:
			Send2Trash.send2trash(str(target))
		else:
			LOG.warning("The user has not confirmed the thrashing of: %s", target)
			return

		LOG.info("Moved to thrash: %s", target)

	# --- Bulk (Clear Folder) ---
	def _preflight_confirm(
			self,
			root: Path,
			*,
			trash: bool,
			recursive: bool,
			include_hidden: bool,
			pattern: Optional[str],
			antipattern: Optional[str],
			shell_pattern: Optional[str],
			threshold: int
	) -> bool:
		"""
		Estimate the number of candidates and ask for confirmation if count ≥ threshold.
		Uses :meth:`Prompter.confirm` when available; otherwise falls back to a plain prompt.

		:param root: The root path.
		:param trash: If True, moves files to trash.
		:param recursive: If True, recursively traverses the directory tree.
		:param include_hidden: If True, includes hidden files.
		:param pattern: Include only names containing this substring.
		:param antipattern: Exclude names containing this substring.
		:param shell_pattern: Shell-like pattern for names (e.g., "*.jpg").
		:param threshold: Maximal number of items to be removed without confirmation.
		:return: True if confirmed or count<threshold; False if the user declined.
		"""
		est = 0
		try:
			for entry in iter_clear_candidates(root, trash=trash, recursive=recursive):
				if not include_hidden and is_hidden_path(root, entry):
					continue
				if not matches_filters(
						entry.name,
						include_hidden=True,
						pattern=pattern,
						antipattern=antipattern,
						shell_pattern=shell_pattern
				):
					continue
				est += 1
				if est >= threshold:
					break
		except PermissionError as exc:
			LOG.warning("Permission error while pre-scanning '%s': %s", root, exc)
			est = threshold

		if est >= threshold:
			msg = f"About to remove at least {est} entr{'y' if est == 1 else 'ies'} from: {root}. Continue?"
			try:
				ask = self._pick_prompt(None, confirm=True)
				return ask(msg)
			except Exception:
				# very defensive fallback
				ans = input(f"{msg} [y/N]: ").strip().lower()
				return ans in {"y", "yes"}
		return True

	def _delete_one(
			self,
			entry: Path,
			*,
			trash: bool,
			recursive: bool,
			follow_symlinks: bool
	) -> None:
		"""
		Delete or trash a single entry (file/dir/symlink).
		Obeys :attr:`dry_run`.

		:param entry: Path to remove.
		:param trash: If True, move to OS trash (Send2Trash).
		:param recursive: For directories, delete contents recursively when not trashing.
		:param follow_symlinks: Follow symlinks to directories when not trashing.
		"""
		if self.dry_run:
			action = "trash" if trash else "delete"
			kind = "symlink" if entry.is_symlink() else ("dir" if entry.is_dir() else "file")
			suffix = " (recursive)" if (not trash and entry.is_dir() and recursive) else ""
			LOG.info(f"[dry-run] %s %s%s: %s", action, kind, suffix, entry)
			return

		if trash:
			self.trash(entry, missing_ok=True)
			return

		if entry.is_symlink():
			_delete_symlink(entry, follow_symlinks=follow_symlinks)
		elif entry.is_file():
			_delete_file(entry)
		if entry.is_dir():
			_delete_dir(entry, recursive=recursive)
		else:
			# Rare FS entries (FIFO, sockets...). Best-effort unlink (3.12+ has missing_ok).
			try:
				entry.unlink(missing_ok=True)  # type: ignore[arg-type]
			except TypeError:
				# fallback for older Python
				try:
					entry.unlink()
				except FileNotFoundError:
					pass

	def clear_folder(
			self,
			folder: PathLike,
			*,
			recursive: bool = True,
			include_hidden: bool = True,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			trash: bool = False,
			follow_symlinks: bool = False,
			missing_ok: bool = False,
			ignore_errors: bool = False,
			confirm_if_over: Optional[int] = None
	) -> int:
		"""
		Remove all entries from a folder while **keeping the folder itself**.

		This method requires the optional dependency ``sciwork.fs.Dirs``.

		By default, removes files and subdirectories **recursively** (like ``rm -rf`` on
		the folder *contents*). When ``trash`` is True, entries are moved to the OS
		recycle bin (requires mod:`Send2Trash`) instead of being permanently deleted.

		Filtering can be applied using a simple substring ``pattern`` and/or
		``antipattern`` (both tested against the entry **name**), or a shell-like
		``glob`` (e.g., ``"*.tmp"``). Hidden files/dirs (names starting with ``.``)
		can be excluded with ``include_hidden=False``.

		Safety rail:
			If ``confirm_is_over`` is set (e.g., 200), a pre-flight pass estimates the
			number of matching entries. If it meets/exceeds the threshold, the user
			is prompted once via ``input_func`` to confirm. On decline, no deletions
			are performed and the method returns 0.

		Respects ``dry_run`` (logs intended actions without touching the filesystem).

		:param folder: Target the folder whose *contents* will be removed.
		:param recursive: If True (default), remove directory trees; when False,
							only direct children are considered (dirs must be empty).
		:param include_hidden: If False, skip entries with any components starting with ``.``
		:param pattern: Keep only entries whose *name* contains this substring.
		:param antipattern: Exclude entries whose *name* contains this substring.
		:param shell_pattern: Optional shell pattern matched against the *name*
								(e.g., ``"*.log"``). Applied in addition to ``pattern`` filters.
		:param trash: Move entries to OS trash instead of deleting permanently.
		:param follow_symlinks: If True and deleting permanently, follow symlinks to dirs
								(dangerous). When ``trash=True``, symlinks are trashed as links.
		:param missing_ok: If True, do not raise when *folder* does not exist.
		:param ignore_errors: If True, log errors and continue; otherwise, re-raise.
		:param confirm_if_over: Threshold for interactive confirmation before deletion.
								If the number of matching entries is >= this value,
								prompt the user via ``input_func``.
		:return: Number of entries removed (or that would be if ``dry_run`` is True).
		:raises FileNotFoundError: If *folder* does not exist and ``missing_ok`` is False.
		:raises NotADirectoryError: If *folder* exists but is not a directory.
		"""
		try:
			from .dirs import Dirs
		except Exception:
			LOG.error("clear_folder requires the optional dependency 'sciwork.fs.Dirs' to work.")
			raise

		root = Dirs().try_get_dir(folder, missing_ok=missing_ok)
		if root is None:
			return 0

		# Safety rail: preflight confirmation
		if confirm_if_over and confirm_if_over > 0:

			if not self._preflight_confirm(
				root,
				trash=trash,
				recursive=recursive,
				include_hidden=include_hidden,
				pattern=pattern,
				antipattern=antipattern,
				shell_pattern=shell_pattern,
				threshold=confirm_if_over
			):
				LOG.warning("User declined clear_folder in %s", root)
				return 0

		removed = 0
		try:
			for entry in iter_clear_candidates(root, trash=trash, recursive=recursive):
				# hidden filter
				if not include_hidden and is_hidden_path(root, entry):
					continue
				# name filters
				if not matches_filters(
						entry.name,
						include_hidden=True,  # hidden paths handled above
						pattern=pattern,
						antipattern=antipattern,
						shell_pattern=shell_pattern
				):
					continue

				try:
					self._delete_one(
						entry,
						trash=trash,
						recursive=recursive,
						follow_symlinks=follow_symlinks
					)
					removed += 1
				except Exception as exc:
					if ignore_errors:
						LOG.error("Failed to delete '%s': %s", entry, exc)
						continue
					raise
		except PermissionError as exc:
			if ignore_errors:
				LOG.warning("Permission error while clearing '%s': %s", root, exc)
			else:
				raise

		LOG.info("Cleared %d entr%s from: %s", removed, "y" if removed == 1 else "ies", root)
		return removed
