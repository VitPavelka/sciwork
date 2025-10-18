# src/sciwork/fs/inspect.py

from __future__ import annotations

import os
import mimetypes

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from ..logutil import get_logger
from ..imports import PIL

from .exif import (
	_read_exif_object,
	_decode_exif_maps,
	_basic_info,
	_dimensions_block,
	_orientation_block,
	_dpi_block,
	_xp_string_block,
	_gps_block,
	_merge,
	_has_useful_data
)

LOG = get_logger(__name__)

__all__ = ["build_metadata", "extract_exif"]


def _iso_utc(ts: float) -> str:
	"""Return ISO-8601 UTC string from a POSIX timestamp."""
	return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def build_metadata(path: Path, *, st: Optional[os.stat_result] = None) -> Dict[str, Any]:
	"""
	Return unified filesystem metadata for *path*.

	Keys:
		- type 'file' | 'dir' | 'symlink'
		- size: int | None (bytes; only for files)
		- created / modified / accessed: ISO-8601 in UTC
		- created_ts/ modified_ts / accessed_ts: float timestamps
		- mime: best-effort MIME type (filename-based)
		- ext: lowercase extension (with dot)

	:param path: Path to the file.
	:param st: Optional stat result.
	:return: Dict with metadata.
	"""
	p = Path(path)
	if st is None:
		try:
			st = p.lstat()  # lstat: follow also symlinks
		except Exception as exc:
			LOG.warning("lstat() failed for %s: %s", p, exc)
			return {}

	kind = "symlink" if p.is_symlink() else ("dir" if p.is_dir() else "file")
	size = int(st.st_size) if p.is_file() else None

	created_ts = float(st.st_ctime)
	modified_ts = float(st.st_mtime)
	accessed_ts = float(st.st_atime)

	created = _iso_utc(created_ts)
	modified = _iso_utc(modified_ts)
	accessed = _iso_utc(accessed_ts)

	mime, _ = mimetypes.guess_type(p.name)
	ext = p.suffix.lower()

	return {
		"type": kind, "size": size,
		"created": created, "modified": modified, "accessed": accessed,
		"created_ts": created_ts, "modified_ts": modified_ts, "accessed_ts": accessed_ts,
		"mime": mime, "ext": ext
	}


def extract_exif(path: Path, *, file_metadata: bool = True) -> Optional[Dict[str, Any]]:
	"""
	Extract basic EXIF metadata from an image file (the best effort).

	Returns a compact dict:
		- ``datetime_original`` (when present), ``datetime``
		- ``camera_make``, ``camera_model``
		- ``dimensions`` (width, height), ``orientation`` (if present)
		- ``dpi`` block (x/y/unit) when available
		- Windows ``XP*`` strings as text (``xp_comment``, ``xp_keywords``)
		- ``gps`` block with ``lat/lon`` (+ optional ``alt``)
		- ``file`` block with basic file metadata (ctime/mtime/size)

	Use Pillow lazily via :mod:`sciwork.imports` proxy. If Pillow is missing,
	the import error will include a friendly hint :)
	"""
	Image = PIL.Image
	ExifTags = PIL.ExifTags

	try:
		with Image.open(path) as img:
			exif = _read_exif_object(img)
			tag_map, gps_map = _decode_exif_maps(exif, ExifTags)

			out: Dict[str, Any] = {}
			_merge(out, _basic_info(tag_map))
			_merge(out, _dimensions_block(tag_map))
			_merge(out, _orientation_block(tag_map))
			_merge(out, _dpi_block(tag_map))
			_merge(out, _xp_string_block(tag_map))
			_merge(out, _gps_block(gps_map))

			if file_metadata:
				out["file"] = build_metadata(path)

			return out if _has_useful_data(out) else None

	except Exception as exc:
		LOG.warning("EXIF parse failed for %s: %s", path, exc, exc_info=True)
		return None
