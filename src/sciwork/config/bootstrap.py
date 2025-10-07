from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Union, Literal, Optional, Mapping
from copy import deepcopy

from . import store

LOG = logging.getLogger(__name__)
PathLike = Union[str, Path]

DEFAULT_PROJECT_SCHEMA: Dict[str, Any] = {
	"data_handler": {
		"data_folderpath": {"type": "str", "required": True},
		"general_keywords": {"type": "str", "required": True},
		"general_antikeywords": {"type": "str", "required": True},
		"header_rows": {"type": ["int", None], "default": None},
		"sheet_names": {"type": ["str", None], "default": None},
		"keywords": {"type": "str", "default": ""},
		"antikeywords": {"type": "str", "default": ""}
	}
}


def bootstrap_json_file(
		name: str,
		*,
		payload: Optional[Mapping[str, Any]] = None,
		prefer: Literal['project', 'user'] = "project",
		app: str = "sciwork",
		overwrite: bool = False,
) -> Path:
	"""
	Ensure a config JSON *name* exists in the resolved configs dir, writing *payload* if missing.

	- If the target file already exists and ``overwrite=False`` (default), nothing is changed.
	- If ``overwrite=True``, the file is atomically overwritten with *payload*.

	Location is chosen via :func:`store.resolve_config_path`:
	- ``prefer='project'`` → <cwd>/<app>/configs/<name>
	- ``prefer='user'`` → ~/.config/<app>/<name> (Windows: %APPDATA%/<app>/<name>)

	:param name: Target filename (e.g., ``"config_projects.json"``).
	:param payload: JSON object to write on the first run (on when overwriting).
	:param prefer: ``'project'``  (default) or ``'user'``.
	:param app: Namespace directory (default ``'sciwork'``).
	:param overwrite: Overwrite even if the file exists.
	:return: Absolute path to the (existing or created) file.
	"""
	dest = store.resolve_config_path(name, prefer=prefer, app=app)

	if dest.exists() and not overwrite:
		LOG.info("Config already exists, keeping it: %s", dest)
		return dest

	if payload is not None and not isinstance(payload, Mapping):
		raise TypeError("payload must be a mapping (JSON object) when provided.")

	effective_payload: Dict[str, Any] = deepcopy(DEFAULT_PROJECT_SCHEMA) if payload is None else payload
	dest.parent.mkdir(parents=True, exist_ok=True)

	existed = dest.exists()
	store.write_json(dest, effective_payload, overwrite=True, backup_ext=".bak" if existed else None)
	LOG.info("%s config %s at %s", "Overwrote" if existed else "Created", name, dest)
	return dest
