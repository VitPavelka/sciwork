# src/sciwork/fs/delete_utils.py

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Iterable

from ..logutil import get_logger

LOG = get_logger(__name__)

__all__ = [
	"rmtree_onerror",
	"delete_file",
	"delete_dir",
	"delete_symlink",
	"iter_clear_candidates"
]


# --- Low-level helpers ---
def rmtree_onerror(
		func: Callable[[str], Any],
		path_str: str,
		exc_info: tuple[type[BaseException], BaseException, TracebackType]
) -> None:
	"""
	Best-effort error handler for :func:`shutil.rmtree`.

	When a removal fails (typically due to a read-only attribute on Windows),
	this handler tries to ``chmod +w`` the offending path and re-executes
	the original OS function.

	:param func: The OS-level function that failed (e.g., ``os.remove``/``os.rmdir``).
	:param path_str: The path that caused the error.
	:param exc_info: Original ``(exc_type, exc_value, exc_traceback)`` tuple.
	:return: Exception: Re-raises if the retry fails as well.
	"""
	try:
		# make writable, then retry the original func
		os.chmod(path_str, stat.S_IWRITE)
		func(path_str)
	except Exception:
		# log the original exception; keep propagating
		LOG.error("rmtree onerror: F´failed to remove %s after chmod +w", path_str, exc_info=exc_info)
		raise


def delete_file(target: Path) -> None:
	"""Unlink a regular file; on permission error try to make it writable and retry.."""
	try:
		target.unlink()
	except PermissionError:
		# try to make writable then retry
		target.chmod(stat.S_IWRITE)
		target.unlink()


def delete_dir(target: Path, *, recursive: bool) -> None:
	"""Remove an empty directory or a whole tree (``recursive=True``)."""
	if recursive:
		shutil.rmtree(target, onerror=rmtree_onerror)
	else:
		target.rmdir()


def delete_symlink(target: Path, *, follow_symlinks: bool) -> None:
	"""
	Remove a symlink. If it points to a directory and ``follow_symlinks=True``,
	delete the *target directory tree*; otherwise unlink the link itself.
	"""
	if follow_symlinks and target.is_dir():
		# follow the link to dir → delete the tree it points to
		shutil.rmtree(target.resolve(), onerror=rmtree_onerror)
	else:
		target.unlink()


def iter_clear_candidates(
		root: Path, *, trash: bool, recursive: bool
) -> Iterable[Path]:
	"""
	Iterate entries to be cleared from *root* (the directory itself is kept).

	:param root: Directory whose *contents* we clear.
	:param trash: When trashing, return only top-level entries (trash can remove trees).
	:param recursive: For permanent delete, optionally traverse recursively (files first).
	:return: Iterable of candidate paths.
	"""
	if trash:
		# Send2Trash can trash trees directly; top-level is enough
		return list(root.iterdir())
	if recursive:
		# Files first, deepest directories later → sort by (is_dir, -depth)
		return sorted(root.rglob("*"), key=lambda p: (p.is_dir(), -len(p.parts)))
	return list(root.iterdir())
