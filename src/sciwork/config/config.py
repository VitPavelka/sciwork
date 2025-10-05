from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Union
from types import TracebackType

from . import loader, schema, templates

LOG = logging.getLogger(__name__)
PathLike = Union[str, Path]


class RobustConfig:
	"""
	Unified, high-level API for loading, merging, validating and generating
	INI/JSON configuration files.
	Internally delegates to sciwork.config.{loader,schema,templates,store}.

	Typical flow:
		rc = RobustConfig()
		rc.load_ini_configs(["job.ini"])
		rc.validate_with_schema_json("config_projects.json", template="data_handler", sections=["main"])

	You can also *generate* skeleton configs from a JSON template:
		rc.create_ini_from_template("config_projects.json", "out.ini", template="data_handler", sections=["main"])
		rc.create_json_from_template("config_projects.json", "out.json", template="data_handler", sections=["main"])
	"""
	def __init__(self) -> None:
		self._data: Dict[str, Dict[str, Any]] = {}
		self._schema_defaults: Dict[str, Dict[str, Any]] = {}

	def __repr__(self) -> str:
		"""Returns string like ``RobustConfig(sections=['main', 'dev'])``."""
		sections = sorted(self._data.keys())
		return f"{self.__class__.__name__}(sections={sections})"

	def __str__(self) -> str:
		"""
		Lists sections and how many keys each section contains. Designed for quick
		diagnostics (not a full dump).
		"""
		if not self._data:
			return "RobustConfig with no sections"

		header = f"RobustConfig with {len(self._data)} section(s):"
		lines = [f"[{sec}] ({len(keys)} keys)" for sec, keys in sorted(self._data.items())]
		return header + "\n" + "\n".join(lines)

	def __enter__(self) -> "RobustConfig":
		"""
		Enable ``with RobustConfig() as rc: ...`` usage.
		No resources are acquired here; this returns ``self`` for convenience.
		"""
		return self

	def __exit__(
			self,
			exc_type: Optional[type[BaseException]],
			exc_val: Optional[BaseException],
			exc_tb: Optional[TracebackType]
	) -> bool:
		"""
		Context-manager exit hook.
		Logs any exception that occurred inside the ``with`` block and returns
		``False`` to let the exception propagate (default Python behavior).

		:return: ``False`` - do not suppress exceptions.
		"""
		if exc_type is not None:
			LOG.error("Exception inside RobustConfig context: %s", exc_type, exc_info=(exc_type, exc_val, exc_tb))
		return False

	# --- Load ---
	def load_ini_config(
			self,
			path: PathLike,
			*,
			interpolation: str = "extended",
			csv_delimiters: Optional[Sequence[str]] = None
	) -> "RobustConfig":
		"""
		Load a single INI file and merge it into the currently loaded data.

		:param path: INI file path.
		:param interpolation: 'extended' for ConfigParser.ExtendedInterpolation, or 'none'.
		:param csv_delimiters: Optional list of delimiters used by the loader for CSV-like parsing.
		:return: self.
		:raises ConfigError: On parsing/IO errors.
		"""
		data, _loaded = loader.load_ini_files(
			[path],
			interpolation=interpolation,
			csv_delimiters=csv_delimiters
		)
		loader.merge_dicts(self._data, data)
		LOG.info("Loaded INI: %s", Path(path).resolve())
		return self

	def load_ini_configs(
			self,
			files: Iterable[PathLike],
			*,
			interpolation: str = "extended",
			csv_delimiters: Optional[Sequence[str]] = None
	) -> "RobustConfig":
		"""
		Load multiple INI files (later override earlier) and merge into current data.

		:param files: Iterable of INI paths.
		:param interpolation: 'extended' or 'none'.
		:param csv_delimiters: Optional list of CSV-like delimiters.
		:return: self.
		:raises ConfigError: On parsing/IO errors.
		"""
		data, _loaded = loader.load_ini_files(
			files,
			interpolation=interpolation,
			csv_delimiters=csv_delimiters
		)
		loader.merge_dicts(self._data, data)
		LOG.info("Loaded %d INI file(s).", len(list(files)))
		return self

	def load_json_config(self, path: PathLike) -> "RobustConfig":
		"""
		Merge a single JSON config (shape: section->key->value) into current data.

		:param path: JSON file path.
		:return: self.
		:raises ConfigError: On read/shape errors.
		"""
		merged = loader.load_json_files([path])
		loader.merge_dicts(self._data, merged)
		LOG.info("Loaded JSON: %s", Path(path).resolve())
		return self

	def load_json_configs(self, files: Iterable[PathLike]) -> "RobustConfig":
		"""
		Merge multiple JSON configs (shape: section->key->value) into current data.

		:param files: Iterable of JSON file paths.
		:return: self.
		:raises ConfigError: On read/shape errors.
		"""
		merged = loader.load_json_files(list(files))
		loader.merge_dicts(self._data, merged)
		LOG.info("Loaded %d JSON(s).", len(list(files)))
		return self

	# --- validate ---
	def validate(self, *, schema_map: Mapping[str, Mapping[str, schema.KeySpec]]) -> "RobustConfig":
		"""
		Validate current data against a KeySpec mapping.

		:param schema_map: Mapping section -> key -> KeySpec
		:return: self.
		:raises ConfigError: On any validation problem.
		"""
		if self._schema_defaults:
			schema.apply_defaults(self._data, self._schema_defaults)
		schema.validate_data(self._data, schema_map)
		LOG.info("Validation OK")
		return self

	def validate_with_schema_json(
			self,
			schema_path: PathLike,
			*,
			template: Optional[str] = None,
			project: Optional[str] = None,
			sections: Optional[Iterable[str]] = None
	) -> "RobustConfig":
		"""
		Convenience: load a JSON schema and validate current data.

		Behavior:
			- If *template* is provided: apply that template to *sections* (or to all
			currently loaded sections when *sections* are None).
			- If *template* is omitted: treat JSON as {section -> key -> spec}, or
			you can add auto-detection later.

		:param schema_path: Path to JSON schema file.
		:param template: Optional template name to apply (e.g. "data_handler").
		:param project: Optional project name when schema has a "projects" wrapper.
		:param sections: Target sections; defaults to current loaded sections.
		:return: self.
		:raises ConfigError: On schema/read/validate errors.
		"""
		# Default target sections = current sections in memory
		section_list = list(sections) if sections is not None else list(self._data.keys())

		if template:
			spec, defaults = schema.load_schema_template_from_json(
				schema_path,
				template=template,
				project=project,
				sections=section_list
			)
		else:
			raw = schema.load_schema_from_json(schema_path)

			# projects, if they exist
			root = raw
			if isinstance(raw, dict) and "projects" in raw and isinstance(raw["projects"], dict):
				root = raw["projects"].get(project, raw["projects"])

			is_template_like = False
			template_name: Optional[str] = None
			if isinstance(root, dict) and len(root) == 1:
				template_name = next(iter(root.keys()))
				maybe_spec = root[template_name]
				if isinstance(maybe_spec, dict):
					for v in maybe_spec.values():
						if isinstance(v, dict) and any(k in v for k in ("type", "required", "default", "choices")):
							is_template_like = True
							break

			if is_template_like and template_name:
				spec, defaults = schema.load_schema_template_from_json(
					schema_path, template=template_name, project=project, sections=section_list
				)
			else:
				spec, defaults = schema.schema_parse_to_keyspecs(raw)

		self._schema_defaults = defaults or {}
		return self.validate(schema_map=spec)

	# --- Create ---
	@staticmethod
	def create_ini_from_template(
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
		Generate an INI file by applying a template object to *sections*.

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
		return templates.write_ini_from_template(
			schema_json_path,
			dest_path,
			template=template,
			sections=sections,
			project=project,
			include_defaults=include_defaults,
			placeholder=placeholder,
			header_comment=header_comment,
			overwrite=overwrite
		)

	@staticmethod
	def create_json_from_template(
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
		Generate a JSON configuration by applying a template object to *sections*.

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
		return templates.write_json_from_template(
			schema_json_path,
			dest_path,
			template=template,
			sections=sections,
			project=project,
			include_defaults=include_defaults,
			placeholder=placeholder,
			drop_nulls=drop_nulls,
			overwrite=overwrite,
			indent=indent
		)

	# --- clearing ---
	def clear(
			self,
			*,
			sections: Optional[Iterable[str]] = None,
			keep_defaults: bool = False
	) -> "RobustConfig":
		"""
		Clear in-memory configuration data (all sections or only selected ones).

		When the *sections* parameter is None (default), all sections are removed.
		Otherwise, only the provided section names are removed (case-insensitive).
		By default, any previously loaded schema defaults are kept;
		pass ``keep_defaults=False`` to clear them as well.

		:param sections: Iterable of section names to delete; ``None`` to clear all.
		:param keep_defaults: Keep schema defaults (``True``) or clear them (``False``, default).
		:return: self (for fluent chaining).
		"""
		if sections is None:
			self._data.clear()
			cleared = "all sections"
		else:
			removed = []
			for name in sections:
				key = str(name).lower()
				if key in self._data:
					self._data.pop(key, None)
					removed.append(key)
			cleared = f"sections={removed or '[]'}"

		if not keep_defaults:
			self._schema_defaults.clear()

		LOG.info("Cleared %s%s",
		         cleared,
		         "" if keep_defaults else " (and schema defaults)")
		return self

	# --- accessors ---
	def to_dict(self) -> Dict[str, Dict[str, Any]]:
		"""Return a deep (but still mutable) dict representation of current data."""
		return self._data

	def section(self, name: str, *, missing_ok: bool = False) -> Dict[str, Any]:
		"""Return one section mapping (lowercased name)"""
		key = name.lower()
		if key not in self._data and not missing_ok:
			raise KeyError(f"Unknown section: {name}")
		return self._data.get(key, {})
