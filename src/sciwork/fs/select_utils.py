# src/sciwork/fs/select_utils.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = [
	"norm_exts", "maybe_rel_one", "maybe_rel_list",
	"normalize_indices", "parse_index_list",
	"sort_fast", "sort_with_meta"
]


# --- Helpers: Indices & Output ---
def norm_exts(exts: Iterable[str]) -> set[str]:
	"""Normalize extensions to the lowercase with a leading dot."""
	return {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}


def maybe_rel_one(p: Path, root: Path, return_absolute: bool) -> Path:
	"""Return a relative path if possible, else absolute."""
	if return_absolute:
		return p
	try:
		return p.relative_to(root)
	except Exception:
		return p


def maybe_rel_list(paths: List[Path], root: Path, return_absolute: bool) -> List[Path]:
	"""Return a list of relative paths if possible, else absolute."""
	if return_absolute:
		return paths
	out: List[Path] = []
	for p in paths:
		try:
			out.append(p.relative_to(root))
		except Exception:
			out.append(p)
	return out


def parse_index_list(spec: str, max_n: int) -> List[int]:
	"""
	Parse comma-separated indices and ranges like ``1,3,5-7`` into a 1-based list.
	"""
	parts = [p.strip() for p in spec.split(",") if p.strip()]
	out: List[int] = []
	seen = set()
	for part in parts:
		if "-" in part:
			a, b = part.split("-", 1)
			start = int(a)
			end = int(b)
			if start > end:
				start, end = end, start
			for i in range(start, end + 1):
				if 1 <= i <= max_n and i not in seen:
					seen.add(i)
					out.append(i)
				else:
					raise ValueError(f"Index out of range (1..{max_n}), got {i}")
		else:
			i = int(part)
			if not (1 <= i <= max_n):
				raise ValueError(f"Index out of range (1..{max_n}), got {i}")
			if i not in seen:
				seen.add(i)
				out.append(i)
	return out


def normalize_indices(indices: Iterable[int], max_n: int) -> List[int]:
	"""Normalize 1-based indices; validate range; de-duplicate & keep order."""
	seen = set()
	out: List[int] = []
	for raw in indices:
		i = int(raw)
		if not (1 <= i <= max_n):
			raise ValueError(f"Index out of range (1..{max_n}), got {i}")
		if i not in seen:
			seen.add(i)
			out.append(i)
	return out


# --- Helpers: Sort ---
def sort_fast(candidates: List[Path], sort_norm: str, descending: bool) -> List[Path]:
	"""Sort plain paths by 'name' or 'ext' only."""
	items: list[Path] = [p if isinstance(p, Path) else Path(p) for p in candidates]

	def key_by_name(p: Path) -> str:
		return p.name.lower()

	def key_by_ext(p: Path) -> str:
		return p.suffix.lower() if p.suffix else ""

	keyfunc = key_by_name if sort_norm == "name" else key_by_ext if sort_norm == "ext" else key_by_name
	return sorted(items, key=keyfunc, reverse=descending)


def sort_with_meta(
		items: List[Tuple[Path, dict]],
		sort_norm: str,
		descending: bool
) -> List[Tuple[Path, dict]]:
	"""Sort (path, metadata) by 'name' | 'ext' | 'ctime' | 'mtime' | 'size'."""
	def key_name(t: tuple[Path, dict]) -> str:
		return t[0].name.lower()

	def key_ext(t: tuple[Path, dict]) -> str:
		return t[0].suffix.lower() if t[0].suffix else ""

	def key_ctime(t: tuple[Path, dict]) -> float:
		return float(t[1].get("created_ts", 0.0))

	def key_mtime(t: tuple[Path, dict]) -> float:
		return float(t[1].get("modified_ts", 0.0))

	def key_size(t: tuple[Path, dict]) -> int:
		return int(t[1].get("size", -1))

	if sort_norm == "name":
		key = key_name
	elif sort_norm == "ext":
		key = key_ext
	elif sort_norm == "ctime":
		key = key_ctime
	elif sort_norm == "mtime":
		key = key_mtime
	elif sort_norm == "size":
		key = key_size
	else:
		raise ValueError(f"sort_by must be one of: 'name', 'ext', 'ctime', 'mtime', 'size': {sort_norm}")
	return sorted(items, key=key, reverse=descending)
