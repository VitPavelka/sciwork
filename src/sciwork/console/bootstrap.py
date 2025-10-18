# src/sciwork/console/bootstrap.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal

from ..logutil import get_logger
from ..config import bootstrap_json_file

LOG = get_logger(__name__)

# Minimal default palette; will be extended later
DEFAULT_ANSI_THEME: Dict[str, Dict[str, str]] = {
	"style": {"RESET": "\u001b[0m"},
	"bfg": {
		"GREEN": "\u001b[92m",
		"CYAN": "\u001b[96m",
		"BLUE": "\u001b[94m",
		"RED": "\u001b[91m",
		"WHITE": "\u001b[97m",
		"YELLOW": "\u001b[93m",
		"MAGENTA": "\u001b[95m",
		"BLACK": "\u001b[90m"
	}
}


def ensure_ansi_colors(
		*,
		prefer: Literal["project", "user"] = "project",
		overwrite: bool = False,
) -> Path:
	"""
	Ensure an ``ansi_colors.json`` exists and return its absolute path.

	The file is created using a minimal default palette unless it already exists
	(unless ``overwrite=True``). By default, it is placed under
	``<cwd>/sciwork/configs/ansi_colors.json``; pass ``prefer='user'`` to use a
	per-user config location (``~/.config/sciwork/`` or ``%APPDATA%\\sciwork\\`` on Windows).

	:param prefer: Where to create/read the file (``'project'`` or ``'user'``).
	:param overwrite: When ``True``, rewrite the file even if it exists.
	:return: Absolute path to the JSON file.
	:raises OSError: On filesystem errors when creating directories or writing the file.
	"""
	path = bootstrap_json_file(
		name="ansi_colors.json",
		payload=DEFAULT_ANSI_THEME,
		prefer=prefer,
		app="sciwork",
		overwrite=overwrite
	)
	LOG.info("ANSI theme ready at: %s", path)
	return path
