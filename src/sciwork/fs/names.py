# src/sciwork/fs/names.py

from __future__ import annotations

from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
import re


__all__ = ["create_timestamped_name"]

_slug_rx = re.compile(r"\s+")


def create_timestamped_name(
		name: str = "",
		*,
		full: bool = True,
		custom_format: Optional[str] = None,
		prepend_date: bool = False,
		tz: Optional[timezone] = None,
		keep_extension: bool = True,
		sep: str = "_"
) -> str:
	"""
	Build a name with an embedded timestamp.

	:param name: Base filename (may include extension).
	:param full: If True, include time (HH_MM_SS) in the default format; else date only.
	:param custom_format: Optional strftime format string to override defaults.
	:param prepend_date: If True, put the date before the name; else append to the end.
	:param tz: Optional timezone; defaults to local time if None.
	:param keep_extension: If True, preserve the extension of *name*.
	:param sep: Separator between pieces.
	:return: Timestamped name string.
	"""
	now = datetime.now(tz=tz)
	fmt = custom_format if custom_format else ("%Y_%m_%d_%H_%M_%S" if full else "%Y_%m_%d")
	stamp = now.strftime(fmt)

	stem, suffix = (name, "")
	if keep_extension and name:
		p = Path(name)
		stem, suffix = (p.stem, p.suffix)

	stem = _slug_rx.sub("_", stem.strip())
	if not stem:
		return f"{stamp}{suffix}"
	return f"{stamp}{sep}{stem}{suffix}" if prepend_date else f"{stem}{sep}{stamp}{suffix}"
