# src/sciwork/fs/filters.py

from __future__ import annotations

import fnmatch
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional, Union

__all__ = [
	"matches_filters",
	"parse_duration_seconds",
	"coerce_time_cutoff",
	"is_hidden_path",
	"mtime_matches",
	"iter_dir_filtered"
]


def matches_filters(
		name: str,
		*,
		include_hidden: bool = True,
		pattern: Optional[str] = None,
		antipattern: Optional[str] = None,
		shell_pattern: Optional[str] = None
) -> bool:
	"""
	Check if a file/directory name matches the given filtering criteria.

	Applies multiple filters in sequence:
	1. Hidden files filter (if include_hidden=False)
	2. Substring included (a pattern)
	3. Substring excluded (an antipattern)
	4. Shell-style pattern matching (e.g., "*.txt")

	:param name: Name of the file/directory to check (not a path).
	:param include_hidden: If False, hidden entries (starting with '.') are excluded.
	:param pattern: Optional substring that must be present in the name.
	:param antipattern: Optional substring that must NOT be present in the name.
	:param shell_pattern: Optional shell-style pattern (e.g., "*.txt") to match against.
	:return: True if the name matches all enabled filters, False otherwise.
	"""
	if not include_hidden and name.startswith("."):
		return False
	if pattern and pattern not in name:
		return False
	if antipattern and antipattern in name:
		return False
	if shell_pattern and not fnmatch.fnmatch(name, shell_pattern):
		return False
	return True


def parse_duration_seconds(spec: str) -> Optional[float]:
	"""
	Parse a human-ish duration like '90s', '15m', '2h', '7d' into seconds.
	Returns None if the format isn't recognized.

	:param spec: String like '90s', '15m', '2h', '7d'.
	:return: Duration in seconds, or None if the format isn't recognized.
	"""
	m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhdSMHD])\s*", spec or "")
	if not m:
		return None
	val = float(m.group(1))
	unit = m.group(2).lower()
	scale = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}
	return val * scale[unit]


def coerce_time_cutoff(
		spec: Optional[Union[float, int, str, datetime]]
) -> Optional[float]:
	"""
	Convert a *time filter* into an absolute POSIX timestamp cutoff.

	Accepted:
	* number → seconds ago from now,
	* ISO 8601 string (``datetime.fromisoformat``),
	* short duration (see :func:`parse_duration_seconds`),
	* datetime (naive assumed UTC).

	:param spec: The filter value or None.
	:return: POSIX timestamp (seconds since the epoch) or None.
	"""
	if spec is None:
		return None

	now = time.time()

	if isinstance(spec, (int, float)):
		return now - float(spec)

	if isinstance(spec, datetime):
		dt = spec if spec.tzinfo else spec.replace(tzinfo=timezone.utc)
		return dt.timestamp()

	if isinstance(spec, str):
		# try ISO 8601 first
		try:
			dt = datetime.fromisoformat(spec)
			if dt.tzinfo is None:
				dt = dt.replace(tzinfo=timezone.utc)
			return dt.timestamp()
		except Exception:
			pass
		# try duration (e.g., '2h', '7d')
		secs = parse_duration_seconds(spec)
		if secs is not None:
			return now - secs

	return None


def is_hidden_path(root: Path, entry: Path) -> bool:
	"""
	Return True if *entry* is hidden relative to *root* (any path part starts with '.').

	:param root: The root path.
	:param entry: The candidate path.
	:return: True when hidden, False otherwise.
	"""
	try:
		rel = entry.relative_to(root)
		return any(part.startswith(".") for part in rel.parts)
	except Exception:
		return entry.name.startswith(".")


def mtime_matches(
		p: Path,
		*,
		older_than: Optional[Union[int, float, str, datetime]] = None,
		newer_than: Optional[Union[int, float, str, datetime]] = None
) -> bool:
	"""
	Check whether ``p.stat().st_mtime`` matches the given time bounds.

	:param p: Path to check.
	:param older_than: Keep entries strictly older than this (see :func:`coerce_time_cutoff`).
	:param newer_than: Keep entries strictly newer than this.
	:return: True if both bounds (when present) pass.
	"""
	try:
		mtime = p.stat().st_mtime
	except Exception:
		return False

	if older_than is not None:
		cutoff = coerce_time_cutoff(older_than)
		if cutoff is not None and not (mtime < cutoff):
			return False

	if newer_than is not None:
		cutoff = coerce_time_cutoff(newer_than)
		if cutoff is not None and not (mtime > cutoff):
			return False

	return True


def iter_dir_filtered(
		root: Path,
		*,
		include_hidden: bool = True,
		pattern: Optional[str] = None,
		antipattern: Optional[str] = None,
		shell_pattern: Optional[str] = None,
		files_only: bool = False,
		older_than: Optional[Union[int, float, str, datetime]] = None,
		newer_than: Optional[Union[int, float, str, datetime]] = None
) -> Iterator[Path]:
	"""
	Iterate over entries in *root* that match name/time filters (non-recursive).

	:param root: Directory to scan.
	:param include_hidden: Ignore hidden if False.
	:param pattern: Substring that is included.
	:param antipattern: Substring that is excluded.
	:param shell_pattern: Shell-like pattern (e.g., "*.txt").
	:param files_only: Yield only files, not directories.
	:param older_than: Optional mtime lower-than cutoff.
	:param newer_than: Optional mtime greater than cutoff.
	:yield: Paths matching filters.
	"""
	for entry in root.iterdir():
		if files_only and not entry.is_file():
			continue
		if not matches_filters(
			entry.name,
			include_hidden=include_hidden,
			pattern=pattern,
			antipattern=antipattern,
			shell_pattern=shell_pattern
		):
			continue
		if older_than is None and newer_than is None:
			yield entry
			continue
		if mtime_matches(entry, older_than=older_than, newer_than=newer_than):
			yield entry
