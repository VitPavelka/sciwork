from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union

from .schema import (
	KeySpec,
	load_schema_template_from_json
)

LOG = logging.getLogger(__name__)
PathLike = Union[str, Path]


# --- Internal helpers
def _ensure_parent(path: Path) -> None:
	"""Create parent directories for *path* if missing."""
	path.parent.mkdir(parents=True, exist_ok=True)


def _to_ini_scalar(value: Any) -> str:
	"""
	Convert a Python value to a string suitable for INI emission.

	Strategy:
		* None -> "null"
		* bool -> "true"/"false"
		* numbers/strings -> str(value)
		* lists/dicts/other -> JSON

	This matches our parser in that:
		- "null" is recognized as None
		- "true"/"false" -> booleans,
		- JSON-like for complex types is safely parseable again.

	:param value: Python value to convert.
	:return: String suitable for INI emission.
	"""
	if value is None:
		return "null"
	if isinstance(value, bool):
		return "true" if value else "false"
	if isinstance(value, (int, float, str)):
		return str(value)
	# lists, dicts, tuples... -> JSON
	try:
		return json.dumps(value, ensure_ascii=False)
	except Exception:
		return str(value)


def _build_mapping_from_schema(
		schema: Mapping[str, Mapping[str, KeySpec]],
		defaults: Mapping[str, Mapping[str, Any]],
		*,
		sections: Optional[Iterable[str]] = None,
		include_defaults: bool = True,
		placeholder: Optional[str] = ""
) -> Dict[str, Dict[str, Any]]:
	"""
	Build a section→key→value mapping from a parsed schema and defaults.

	If *sections* are provided, only those sections are included. Otherwise,
	all sections found in *schema* are used.

	:param schema: Section → key → KeySpec.
	:param defaults: Section → key → default (optional keys only).
	:param sections: Optional subset of section names to include.
	:param include_defaults: When True, use defaults where available.
	:param placeholder: Value used for keys without defaults (can be '', None, or text).
	:return: Dictionary ready to be dumped as INI/JSON content.
	"""
	target_sections = list(sections) if sections else list(schema.keys())
	out: Dict[str, Dict[str, Any]] = {}

	for sec in target_sections:
		keyspecs = schema.get(sec, {})
		sec_defaults = defaults.get(sec, {}) if include_defaults else {}
		bucket: Dict[str, Any] = {}

		for key, spec in keyspecs.items():
			if include_defaults and key in sec_defaults:
				bucket[key] = sec_defaults[key]
			else:
				bucket[key] = placeholder
		out[sec] = bucket

	return out


# --- Public API: render and write INI / JSON from template schema
def render_ini_from_template(
		schema_json_path: PathLike,
		*,
		template: str,
		sections: Iterable[str],
		project: Optional[str] = None,
		include_defaults: bool = True,
		placeholder: Optional[str] = ""
) -> Tuple[str, Dict[str, Dict[str, Any]]]:
	"""
	Render an INI text from a JSON schema **template** applied to many sections.

	This function:
		1) loads a schema JSON file (optionally inside a ``projects`` wrapper),
		2) extracts the chosen ``template`` object,
		3) applies it to the provided *sections*,
		4) returns an INI-formatted string and the intermediate mapping used.

	:param schema_json_path: Path to the schema JSON.
	:param template: Template object name in the schema (e.g., ``"data_handler"``).
	:param sections: Section names to include in the generated INI.
	:param project: Optional project name when schema uses a ``"projects"`` wrapper.
	:param include_defaults: Insert defaults from schema when available.
	:param placeholder: Value for keys without defaults (e.g., ``""`` or ``"<fill>"``).
	:return: ``(ini_text, mapping)`` where *mapping* is ``section -> key -> value``.
	:raises ConfigError: On IO/parse errors or invalid schema shapes.
	"""
	# Parse schema template → (KeySpec mapping, defaults)
	parsed_schema, defaults = load_schema_template_from_json(
		schema_json_path,
		template=template,
		project=project,
		sections=list(sections)
	)
	mapping = _build_mapping_from_schema(
		parsed_schema,
		defaults=defaults,
		sections=sections,
		include_defaults=include_defaults,
		placeholder=placeholder
	)

	# Compose INI text manually (we avoid extra interpolation side effects)
	lines: list[str] = []
	for sec in mapping:
		lines.append(f"[{sec}]")
		for key, val in mapping[sec].items():
			lines.append(f"{key} = {_to_ini_scalar(val)}")
		lines.append("")  # blank line between sections

	ini_text = "\n".join(lines).rstrip() + "\n"
	return ini_text, mapping


def write_ini_from_template(
		schema_json_path: PathLike,
		dest_path: PathLike,
		*,
		template: str,
		sections: Iterable[str],
		project: Optional[str] = None,
		include_defaults: bool = True,
		placeholder: Optional[str] = "",
		header_comment: Optional[str] = None,
		overwrite: bool = False,
) -> Path:
	"""
	Generate and write an INI file from a schema **template**.

	:param schema_json_path: Path to the schema JSON.
	:param dest_path: Where to write the INI file.
	:param template: Template object name (e.g., ``"data_handler"``).
	:param sections: Section names to include.
	:param project: Optional project name when using ``"projects"`` wrapper.
	:param include_defaults: Insert defaults when present in schema.
	:param placeholder: Placeholder value for keys without defaults.
	:param header_comment: Optional multi-line text to add at the top as ``;`` comments.
	:param overwrite: When False and file exist, it raises ``FileExistsError``.
	:return: Absolute path to the written INI file.
	:raises FileExistsError: If the destination exists and ``overwrite=False``.
	:raises OSError: On write errors.
	:raises ConfigError: On schema/template errors.
	"""
	dest = Path(dest_path).resolve()
	if dest.exists() and not overwrite:
		raise FileExistsError(f"Destination already exists: {dest}")

	ini_text, _ = render_ini_from_template(
		schema_json_path,
		template=template,
		sections=sections,
		project=project,
		include_defaults=include_defaults,
		placeholder=placeholder
	)

	_ensure_parent(dest)
	try:
		with dest.open("w", encoding="utf-8", newline="\n") as fh:
			if header_comment:
				for line in header_comment.strip("\n").splitlines():
					fh.write(f";{line}\n")
				fh.write("\n")
			fh.write(ini_text)
	except Exception as exc:
		LOG.exception("Failed writing INI to %s: %s", dest, exc)
		raise
	LOG.info("Wrote INI template to %s", dest)
	return dest


def render_json_from_template(
		schema_json_path: PathLike,
		*,
		template: str,
		sections: Iterable[str],
		project: Optional[str] = None,
		include_defaults: bool = True,
		placeholder: Optional[str] = "",
		drop_nulls: bool = False
) -> Dict[str, Dict[str, Any]]:
	"""
	Render a JSON-serializable mapping from a schema **template**.

	:param schema_json_path: Path to the schema JSON.
	:param template: Template object name (e.g., ``"data_handler"``).
	:param sections: Section names to include.
	:param project: Optional project name when schema uses ``"projects"`` wrapper.
	:param include_defaults: Insert defaults from schema when available.
	:param placeholder: Value for keys without defaults (e.g., ``""``).
	:param drop_nulls: If True, omit keys whose value is ``None``.
	:return: A mapping ``section -> {key: value}`` is ready for JSON dumping.
	:raises ConfigError: On schema/template errors.
	"""
	parsed_schema, defaults = load_schema_template_from_json(
		schema_json_path,
		template=template,
		project=project,
		sections=list(sections),
	)
	mapping = _build_mapping_from_schema(
		parsed_schema,
		defaults,
		sections=sections,
		include_defaults=include_defaults,
		placeholder=placeholder,
	)

	if drop_nulls:
		for sec, kv in list(mapping.items()):
			mapping[sec] = {k: v for k, v in kv.items() if v is not None}
	return mapping


def write_json_from_template(
		schema_json_path: PathLike,
		dest_path: PathLike,
		*,
		template: str,
		sections: Iterable[str],
		project: Optional[str] = None,
		include_defaults: bool = True,
		placeholder: Optional[str] = "",
		drop_nulls: bool = False,
		overwrite: bool = False,
		indent: int = 2
) -> Path:
	"""
	Generate and write a JSON configuration from a schema **template**.

	:param schema_json_path: Path to the schema JSON.
	:param dest_path: Destination JSON file path.
	:param template: Template object name.
	:param sections: Section names to include in output.
	:param project: Optional project name when using a ``"projects"`` wrapper.
	:param include_defaults: Insert defaults when present in schema.
	:param placeholder: Placeholder value for missing defaults.
	:param drop_nulls: Remove keys with the value ``None`` from the output.
	:param overwrite: When False and file exist, it raises ``FileExistsError``.
	:param indent: JSON indent for readability (default 2).
	:return: Absolute path to a written JSON file.
	:raises FileExistsError: If the destination exists and ``overwrite=False``.
	:raises OSError: On write errors.
	:raises ConfigError: On schema/template errors.
	"""
	dest = Path(dest_path).resolve()
	if dest.exists() and not overwrite:
		raise FileExistsError(f"Destination already exists: {dest}")

	payload = render_json_from_template(
		schema_json_path,
		template=template,
		sections=sections,
		project=project,
		include_defaults=include_defaults,
		placeholder=placeholder,
		drop_nulls=drop_nulls,
	)

	_ensure_parent(dest)
	try:
		with dest.open("w", encoding="utf-8") as fh:
			json.dump(payload, fh, ensure_ascii=False, indent=indent)
	except Exception as exc:
		LOG.exception("Failed writing JSON to %s: %s", dest, exc)
		raise
	LOG.info("Wrote JSON template to %s", dest)
	return dest
