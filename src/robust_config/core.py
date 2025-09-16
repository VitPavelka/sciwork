"""
Author: Vít Pavelka
Date of last update: 2025/09/16

Version 0.1.0
[+] Initial version.
"""
from __future__ import annotations

if __name__ == "__main__" and __package__ is None:
	import sys
	import pathlib
	sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import ast
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union

import configparser

_TYPE_MAP: Dict[str, type] = {
	"str": str,
	"int": int,
	"float": float,
	"bool": bool,
	"null": type(None),
	"list": list,
	"dict": dict
}


def _parse_type_tokens(type_field: Union[str, List[Any]]) -> Tuple[type, ...]:
	"""
	Convert a JSON schema 'type' field into Python types for KeySpec.expected_type.

	Supports tokens:
		- base: "str", "int", "float", "bool", "null", "list", "dict"
		- parametric: "list[str]" (interpreted for expected_type just as "list")
		- list of tokens means logical OR, e.g. ["int", "null"]
		- JSON literal null is accepted directly (mapped to NoneType)

	:param type_field: String token (e.g., "str") or list of tokens (e.g., ["int", "null"] or ["int", null]).
	:return: Tuple of Python types that are acceptable for KeySpec.expected_type.
	"""
	def _one(token: Any) -> type:
		# JSON null → Python None → map to NoneType
		if token is None:
			return type(None)

		# Normalize to string when possible
		if isinstance(token, str):
			t = token.strip().lower()
		else:
			# be defensive: coerce to str (e.g., 123 → "123"); unknowns fall back to str
			t = str(token).strip().lower()

		if t.startswith("list[") and t.endswith("]"):
			return list
		if t in _TYPE_MAP:
			return _TYPE_MAP[t]
		# Fallback: treat unknown token as 'str'
		return str

	if isinstance(type_field, str) or type_field is None:
		return (_one(type_field),)
	return tuple(_one(tok) for tok in type_field)


def _make_choices_validator(choices: List[Any]) -> Validator:
	"""
	Build a validator that enforces membership in 'choices'.

	:param choices: A list of allowed values.
	:return: Validator function that raises on invalid context.
	"""
	def _validate(value: Any) -> None:
		if value not in choices:
			raise ValueError(f"Value '{value!r}' not in allowed choices {choices}")
	return _validate


# ------------------------- Logging setup ----------------------------------
LOG = logging.getLogger("robust_config")
if not LOG.handlers:
	handler = logging.StreamHandler()
	formatter = logging.Formatter("[%(levelname)s] %(message)s")
	handler.setFormatter(formatter)
	LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)
LOG.propagate = False


def install_global_exception_logging() -> None:
	"""Install a sys.excepthook that logs uncaught exceptions to LOG (incl. tracebacks)"""
	import sys

	def _hook(exc_type, exc, tb):
		LOG.exception("Uncaught exception", exc_info=(exc_type, exc, tb))
	sys.excepthook = _hook


def enable_file_logging(
		log_path: Union[str, os.PathLike] = None,
		level: Union[int, str, None] = None,
		overwrite: bool = True
) -> None:
	"""
	Enable logging to a file. By default, writes to 'logs/robust_config.log'
	next to this module file.

	:param log_path: Path to the logfile. If None, defaults to <module_dir>/logs/robust_config.log.
	:param level: Optional log level for the file handler (e.g., "DEBUG" or logging.DEBUG).
	:param overwrite: If True, truncate the file on each run (mode='w'); else append (mode='a').
	"""
	base_dir = Path(__file__).resolve().parent
	default_path = base_dir / "logs" / "robust_config.log"
	path = Path(log_path) if log_path is not None else default_path
	path.parent.mkdir(parents=True, exist_ok=True)

	mode = "w" if overwrite else "a"
	file_handler = logging.FileHandler(path, mode=mode, encoding="utf-8", delay=True)
	file_formatter = logging.Formatter(
		"%(asctime)s [%(levelname)s] %(name)s: %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S"
	)
	file_handler.setFormatter(file_formatter)
	if level is not None:
		if isinstance(level, str):
			level = getattr(logging, level.upper(), logging.DEBUG)
		file_handler.setLevel(level)
	LOG.addHandler(file_handler)


# ------------------------- Exceptions ----------------------------------
class ConfigError(Exception):
	"""
	Custom exception for configuration-related errors.

	Keep it simple for now; later it should be extended to carry
	context like section/key/file and human-friendly hint.
	"""
	pass


# ------------------------- Helper types ----------------------------------
Validator = Callable[[Any], None]


@dataclass
class KeySpec:
	"""
	Specification for a configuration key used during validation.

	:param expected_type: Allowed type (or tuple of types) for the key value.
	:param required: Whether the key must be present.
	:param validator: Optional callable that receives the parsed value and
						raises on invalid value.
	"""
	expected_type: Union[type, Tuple[type, ...]]
	required: bool = False
	validator: Optional[Validator] = None

	def __post_init__(self) -> None:
		# normalize expected_type to a tuple of types
		et = self.expected_type
		if isinstance(et, type):
			object.__setattr__(self, "expected_type", (et,))
		elif isinstance(et, tuple):
			# ensure all elements are types
			if not et or not all(isinstance(t, type) for t in et):
				raise TypeError("KeySpec.expected_type must be a type or tuple of types")
		else:
			# allow a user mistake like a list[...], convert to tuple if possible
			try:
				candidate = tuple(et)  # type: ignore[arg-type]
			except Exception as exc:
				raise TypeError("KeySpec.expected_type must be a type or tuple of types") from exc
			if not candidate or not all(isinstance(t, type) for t in candidate):
				raise TypeError("KeySpec.expected_type must be a type or tuple of types")
			object.__setattr__(self, "expected_type", candidate)

		# validator must be callable or None
		if self.validator is not None and not callable(self.validator):
			raise TypeError("KeySpec.validator must be callable or None")


# ------------------------- Core utility ----------------------------------
class RobustConfig:
	"""
	Robust INI configuration loader with layering, typing, and validation.

	This class wraps :class: 'configparser.ConfigParser' and projects values
	into typed Python objects. It also supports optional inheritance between
	sections and future schema validation.
	"""

	def __init__(
			self,
			*,
			env_prefix: str = "CONF",
			csv_delimiters: Optional[str] = None,
			interpolation: str = "extended",  # "extended or "none"
	) -> None:
		"""
		Initialize an empty configuration holder.

		:param env_prefix: Prefix for environment variable overrides (e.g.,
							"CONF__SECTION__KEY"). Currently, stored only; the
							application of env overrides lives in a later method.
		:param csv_delimiters: If "None" (default), do **not** split plain strings
								into lists. If a string of delimiter characters
								(e.g., ",;    "), plain strings containing any
								of these characters will be split into lists
								**after** literal parsing succeeds or when
								literal parsing is not applicable.
		:param interpolation: "extended" (default) to enable ${...} style
								interpolation, or "none" to disable interpolation
								(treat '$' as a literal).
		"""
		interp = configparser.ExtendedInterpolation() if \
			str(interpolation).lower() in {"none", "no", "off", "false", "f", "raw"} else None
		self._config = configparser.ConfigParser(interpolation=interp)
		self._loaded_files: List[Path] = []
		self._data: Dict[str, Dict[str, Any]] = {}
		self.env_prefix = env_prefix
		self.csv_delimiters = csv_delimiters
		self.interpolation = "none" if interp is None else "extended"
		self._schema_defaults: Dict[str, Dict[str, Any]] = {}

	def __repr__(self) -> str:
		"""
		Return an unambiguous representation for debugging.

		:return: Includes the env prefix, whether CSV splitting is enabled,
		the loaded files, and the current section list.
		"""
		files = [str(p) for p in self._loaded_files]
		sections = sorted(self._data.keys())
		return (
			f"RobustConfig(env_prefix={self.env_prefix!r}, "
			f"csv_delimiters={self.csv_delimiters!r}, "
			f"files={files!r}, sections={sections!r})"
		)

	def __str__(self) -> str:
		"""
		:return: A concise, human-friendly summary string.
		"""
		files = ",".join(str(p) for p in self._loaded_files) or "<none>"
		sections = ",".join(sorted(self._data.keys())) or "<none>"
		return f"RobustConfig: files[{files}] | sections[{sections}]"

	def __enter__(self) -> "RobustConfig":
		"""
		Enable "with RobustConfig() as rc: ..." usage.

		The class does not hold external resources; this is provided purely
		for ergonomic symmetry. No special setup is performed.
		:return: The "self".
		"""
		return self

	def __exit__(self, exc_type, exc, tb) -> bool:
		"""No-op context manager exit; does not suppress exceptions."""
		return False

	# ------------------- load helpers -------------------------------------------
	@staticmethod
	def _postprocess(value: Any) -> Any:
		"""
		Normalize parsed literal values.
		Turns tuples into lists for config-friendliness; otherwise,
		returns the value unchanged.

		:param value: The value after literal parsing.
		:return: Possibly normalized value (e.g., tuple -> list).
		"""
		if isinstance(value, tuple):
			return list(value)
		return value

	@staticmethod
	def _split_delimited(text: str, delimiters: str) -> List[str]:
		"""
		Split a string on any of the given delimiter characters.

		Respects quotes (single or double) and backslash escapes inside
		quoted segments. Empty tokens are discarded after trimming.

		:param text: Input string to split.
		:param delimiters: A string where *each character* is treated as a
							delimiter (e.g., ",; ").
		:return: List of items (trimmed items without surrounding quotes).
		"""
		parts: List[str] = []
		buffer: List[str] = []
		quote_char: Optional[str] = None
		idx = 0
		while idx < len(text):
			char = text[idx]
			if quote_char:
				if char == "\\" and idx + 1 < len(text):
					buffer.append(text[idx + 1])
					idx += 2
					continue
				if char == quote_char:
					quote_char = None
				else:
					buffer.append(char)
			else:
				if char in ('"', "'"):
					quote_char = char
				elif char in delimiters:
					token = "".join(buffer).strip()
					if token:
						parts.append(token)
					buffer.clear()
				else:
					buffer.append(char)
			idx += 1
		token = "".join(buffer).strip()
		if token:
			parts.append(token)
		return parts

	def _parse_value(self, raw: str) -> Any:
		"""
		Parse a raw string from ini into a typed Python value.

		The parser attempts, in order:
			1. "ast.literal_eval" for safe Python literals (numbers, strings,
				lists, dicts, booleans, "None"). If this yields a *string* and
				:attr: '_csv_delimiters' is set and present in the string, the string
				is further split into a list using those delimiters.
			2. Common textual "None" markers ("none", "null", "na", "n/a").
			3. Booleans ("true/yes/on" → "True", "false/no/off" → "False").
			4. If :attr: '_csv_delimiters' is configured and any is found in the
				text, split into a list (items parsed recursively).
			5. Numeric fallback (int/float) where reasonable.
			6. Otherwise, return the original string.

		:param raw: String as read by :mod: 'configparser'.
		:return: Parsed value with a best-effort type.
		"""
		text = raw.strip()
		# 1) Safe Python literals
		try:
			value = ast.literal_eval(text)
			# Post-process tuples -> lists
			value = self._postprocess(value)
			# If a quoted string contains configured delimiters, split it
			if (
				isinstance(value, str)
				and self.csv_delimiters
				and any(d in value for d in self.csv_delimiters)
			):
				items = self._split_delimited(value, self.csv_delimiters)
				return [self._parse_value(item) for item in items]
			return value
		except Exception:
			pass
		# 2) None-like markers
		if text.lower() in {"none", "null", "na", "n/a"}:
			return None
		# 3) Booleans
		if text.lower() in {"true", "yes", "on"}:
			return True
		if text.lower() in {"false", "no", "off"}:
			return False
		# 4) Simple CSV
		if self.csv_delimiters and any(d in text for d in self.csv_delimiters):
			items = self._split_delimited(text, self.csv_delimiters)
			return [self._parse_value(item) for item in items]
		# 5) Numbers
		try:
			if "." in text:
				return float(text)
			return int(text)
		except ValueError:
			# 6) String fallback
			return text

	def _project_configparser_to_dict(
			self, config: configparser.ConfigParser
	) -> Dict[str, Dict[str, Any]]:
		"""
		Transform a ConfigParser into a nested "dict" with typed values.
		Each section becomes a key in the outer dict; each option appears as a
		lowercased key in the inner dict with its parsed value.

		:param config: A populated :class: 'configparser.ConfigParser' instance.
		:return: The "dict" mapping section → (dict of keys → parsed value).
		"""
		out: Dict[str, Dict[str, Any]] = {}
		for section in config.sections():
			section_dict: Dict[str, Any] = {}
			try:
				for key, raw_value in config.items(section):
					section_dict[key.lower()] = self._parse_value(raw_value)
			except (configparser.InterpolationError, configparser.InterpolationSyntaxError) as exc:
				raise ConfigError(
					f"Interpolation error in section [{section}]: {exc}. "
					f"If your values contain '$', run with interpolation='none' "
					f"or use '$$' to escape."
				) from exc
			out[section.lower()] = section_dict
		return out

	def _merge_chain(self, section: str, visited: Dict[str, bool]) -> Dict[str, Any]:
		"""
		Recursively merge a section with its parents from "extends".

		:param section: Section name to resolve (lowercased key in "_data").
		:param visited: Cycle guard; tracks sections already processed.
		:return: The fully merged dict for "section" (also stored in "_data").
		:raises ConfigError: If a parent listed in "extends" is missing.
		"""
		if section in visited:
			return self._data.get(section, {})
		visited[section] = True

		current = self._data.get(section, {})
		parents_raw = current.get("extends")
		if not parents_raw:
			return current

		parents = parents_raw if isinstance(parents_raw, list) else [parents_raw]
		merged: Dict[str, Any] = {}
		for parent in parents:
			parent_name = str(parent).lower()
			if parent_name not in self._data:
				raise ConfigError(f"[{section}] extends unknown section '{parent_name}'")
			merged.update(self._merge_chain(parent_name, visited))
		# Shadow parent keys with child's own keys (excluding 'extends')
		merged.update({key: value for key, value in current.items() if key != "extends"})
		self._data[section] = merged
		return merged

	def _resolve_inheritance(self) -> None:
		"""
		Resolve "extends" chains for all sections in "_data".

		This populates "_data" such that each section already includes keys
		from its parent sections listed in "extends".
		"""
		visited: Dict[str, bool] = {}
		for section in list(self._data.keys()):
			self._merge_chain(section, visited)

	# ---- Loaders --------------------------------------------------------
	def load(self, files: Iterable[Union[str, os.PathLike]]) -> "RobustConfig":
		"""
		Load one or more INI files; later files override earlier ones.

		Paths are read in the given order. After loading, values are projected
		into a nested "dict" with typed values and section inheritance is resolved.

		:param files: Iterable of filesystem paths ("str" or "PathLike").
		:return: The "self" for fluent chaining.
		:raises ConfigError: If any file is missing or cannot be read.
		"""
		LOG.info("Loading INI files: %s", ",".join(str(Path(p)) for p in files))

		paths = [Path(p) for p in files]
		missing = [str(p) for p in paths if not p.exists()]
		if missing:
			raise ConfigError(f"Missing config file(s): {', '.join(missing)}")

		for path in paths:
			try:
				with path.open("r", encoding="utf-8") as file_handle:
					self._config.read_file(file_handle)
				self._loaded_files.append(path)
				LOG.info("Loaded INI file: %s", path)
			except Exception as exc:
				raise ConfigError(f"Failed reading '{path}': {exc}") from exc

		# Project into typed dict now; allows overrides/validation downstream
		self._data = self._project_configparser_to_dict(self._config)
		self._resolve_inheritance()
		LOG.info("Resolved sections after inheritance: %s", ", ".join(sorted(self._data.keys())))
		return self

	# ----- Overrides & access ------------------------------------------------
	def apply_env_overrides(self) -> "RobustConfig":
		"""
		Apply overrides from environment variables.

		Pattern: "<<ENV_PREFIX>>__<SECTION>__KEY=VALUE" (case-insensitive for
		section/key). The value is parsed via :meth: '_parse_value'.

		Example with the default prefix "CONF":

			export CONF__MAIN__HEADER_ROWS=0
			export CONF__MAIN__GENERAL_KEYWORDS='["_", "extra"]'

		:return: The "self" for fluent chaining.
		"""
		prefix = f"{self.env_prefix}__"
		for env_key, raw_value in os.environ.items():
			if not env_key.startswith(prefix):
				continue
			remainder = env_key[len(prefix):]
			try:
				section_name, key_name = remainder.split("__", 1)
			except ValueError:
				LOG.warning("Ignoring malformed env var override '%s' (expected PREFIX__SECTION__KEY)", env_key)
				continue
			section_name = section_name.lower()
			key_name = key_name.lower()
			value = self._parse_value(raw_value)
			if section_name not in self._data:
				self._data[section_name] = {}
			self._data[section_name][key_name] = value
			LOG.debug("env override: %s.%s=%r", section_name, key_name, value)
			LOG.info("Applied ENV overrides with prefix '%s'", self.env_prefix)
		return self

	def apply_overrides(self, overrides: Iterable[str]) -> "RobustConfig":
		"""
		Apply CLI-style overrides of the form "section.key=value".

		Only the *first* "=" is treated as the separator to allow values that
		themselves contain "=". The key part is split on the *first* "." into
		"section" and "key". Section and key are treated case-insensitively.

		:param overrides: Iterable of override strings (e.g., produced by
							"argparse" with "-o"/"--override").
		:return: The "self" for fluent chaining.
		:raises ConfigError: If an item has an invalid format.
		"""
		for item in overrides or []:
			try:
				left, right = item.split("=", 1)
				section_part, key_part = left.split(".", 1)
			except ValueError as exc:
				raise ConfigError(
					f"Invalid override '{item}'. Use format section.key=value."
				) from exc
			section_name = section_part.strip().lower()
			key_name = key_part.strip().lower()
			value = self._parse_value(right.strip())
			if section_name not in self._data:
				self._data[section_name] = {}
			self._data[section_name][key_name] = value
			LOG.debug("override: %s.%s=%r", section_name, key_name, value)
			LOG.info("Applied %d CLI override(s).", len(list(overrides or [])))
		return self

	def sections(self) -> List[str]:
		"""Return a sorted list of section names."""
		return sorted(self._data.keys())

	def get(self, section: str, key: str, default: Any = None) -> Any:
		"""
		Get a single value from a section (case-insensitive), or default if missing.

		:param section: Section name.
		:param key: Key name.
		:param default: Fallback when the key is not present (a section must exist).
		:return: The value or the default.
		:raises ConfigError: If the section does not exist.
		"""
		s = section.lower()
		if s not in self._data:
			available = ", ".join(self.sections()) or "<none>"
			raise ConfigError(f"Section '{section}' not found. Available sections: {available}")
		return self._data[s].get(key.lower(), default)

	def section(self, name: str) -> Dict[str, Any]:
		"""
		Get a *copy* of a section dict.

		:param name: Section name (case-insensitive).
		:return: Copy of the section mapping (key → typed value).
		:raises ConfigError: If the section does not exist.
		"""
		section_key = name.lower()
		if section_key not in self._data:
			available = ", ".join(sorted(self._data)) or "<none>"
			raise ConfigError(
				f"Section '{name}' not found. Available sections: {available}"
			)
		# Return a shallow copy so callers cannot mutate internal state by accident
		return dict(self._data[section_key])

	def to_dict(self) -> Dict[str, Dict[str, Any]]:
		"""
		Return a deep-ish copy of the internal data structure.

		Both the outer and inner dictionaries are copied to prevent accidental
		mutation of internal state by the caller.

		:return: The "dict" of sections with per-key typed values.
		"""
		return {section: dict(values) for section, values in self._data.items()}

	def validate(self, *, schema: Mapping[str, Mapping[str, KeySpec]]) -> "RobustConfig":
		"""
		Validate presence and types of keys according to a schema.

		For each section defined in "schema" the method checks:
			* if "required" keys are present,
			* whether the value is an instance of the expected_types,
			* and runs the optional "validator".

		All problems are accumulated and reported together for better UX.

		:param schema: Mapping of section name → mapping of the key → :class: "KeySpec".
		:return: The "self" (useful for fluent chaining).
		:raises ConfigError: If any validation error occurs.
		"""
		# Apply defaults (if any) before performing validations
		self._schema_apply_defaults()

		errors: List[str] = []
		for section_name, key_specs in (schema or {}).items():
			values = self._data.get(section_name, {})
			for key_name, spec in key_specs.items():
				if spec.required and key_name not in values:
					errors.append(f"[{section_name}] missing required key '{key_name}'")
					continue
				if key_name not in values:
					continue

				val = values[key_name]
				if not isinstance(val, spec.expected_type):
					errors.append(
						f"[{section_name}] key '{key_name}' expected {spec.expected_type}, "
						f"got {type(val)} ({val!r})"
					)

				validator_fn = getattr(spec, "validator", None)
				if validator_fn is not None:
					if not callable(validator_fn):
						errors.append(
							f"[{section_name}] key '{key_name}' has a non-callable validator "
							f"of type {type(validator_fn)}: {validator_fn}"
						)
					else:
						try:
							validator_fn(val)
						except Exception as exc:
							errors.append(f"[{section_name}] key '{key_name}' validation failed: {exc}")
		if errors:
			hint = (
				"Use --dump pretty to inspect values; overrides can be applied via "
				"env (CONF__SEC__KEY) or CLI --override SEC.key=val."
			)
			raise ConfigError("\n".join(errors) + "\n\n" + hint)
		return self

	@staticmethod
	def _format_pretty(data: Mapping[str, Mapping[str, Any]]) -> str:
		"""
		Human-friendly pretty-printer used by :meth: 'dump'.

		Sections and keys are sorted alphabetically; values use "repr" to make
		types visible (e.g., strings are quoted).

		:param data: Mapping to render (usually the result of :meth: 'to_dict').
		:return: Multi-line string.
		"""
		lines: List[str] = []
		for section_name in sorted(data):
			lines.append(f"[{section_name}]")
			for key, value in sorted(data[section_name].items()):
				lines.append(f"  {key} = {value!r}")
			lines.append("")
		return "\n".join(lines).rstrip()

	def dump(self, fmt: str = "pretty", sections: Optional[List[str]] = None) -> str:
		"""
		Serialize the configuration to a string for display or export.

		:param fmt: Output format - "pretty" (default) or "json".
		:param sections: Optional list of section names to include; if omitted,
							all sections are included.
		:return: String with the rendered configuration.
		:raises ConfigError: If an unsupported format is requested.
		"""
		data = self.to_dict()
		if sections:
			wanted = {s.lower() for s in sections}
			data = {name: values for name, values in data.items() if name in wanted}
		if fmt == "json":
			return json.dumps(data, indent=2, ensure_ascii=False)
		if fmt == "pretty":
			return self._format_pretty(data)
		raise ConfigError("Unsupported dump format. Use 'pretty' or 'json'.")

	@staticmethod
	def _read_json_object(path_like: Union[str, os.PathLike], what: str) -> Dict[str, Any]:
		"""
		Read a JSON file and ensure the top-level is an object (dict).

		:param path_like: Path to the JSON file.
		:param what: Short description of the purpose (e.g., "JSON config", "schema JSON")
						for the error messages.
		:return: The parsed JSON object as a dict.
		:raises ConfigError: If the file is missing, it cannot be read or the
								top-level is not an object.
		"""
		path = Path(path_like)
		if not path.exists():
			raise ConfigError(f"Missing {what}: {path}")
		try:
			with path.open("r", encoding="utf-8") as file_handle:
				payload = json.load(file_handle)
		except Exception as exc:
			raise ConfigError(f"Failed reading {what} '{path}': {exc}") from exc
		if not isinstance(payload, dict):
			raise ConfigError(f"{what} must be a JSON object at top level.")
		return payload

	def apply_json_files(self, files: Iterable[Union[str, os.PathLike]]) -> "RobustConfig":
		"""
		Merge one or more JSON configuration files into the current data.

		JSON expected shape (lowercasing is applied on section/key names):
			{
				"section_a": { "key1": 123, "key2": "abc" },
				"section_b": { "k": [1, 2, 3] }
			}

		:param files: Iterable of JSON file paths.
		:return: The self.
		:raises ConfigError: If a file cannot be read or parsed as JSON.
		"""
		for path_like in files:
			payload = self._read_json_object(path_like, "JSON config")
			for section_name, mapping in payload.items():
				if not isinstance(mapping, dict):
					raise ConfigError(f"Section '{section_name}' in '{path_like}' must be an object.")
				s = section_name.lower()
				self._data.setdefault(s, {})
				for key_name, value in mapping.items():
					k = str(key_name).lower()
					# Values are already native JSON types; keep as-is
					self._data[s][k] = value
					LOG.debug("JSON merge: %s.%s=%r (from %s)", s, k, value, path_like)
		return self

	@staticmethod
	def _schema_resolve_root(raw: Dict[str, Any], project: Optional[str]) -> Dict[str, Any]:
		"""
		Resolve the schema root either directly (sections) or via the 'projects' wrapper.

		If the loaded JSON has the shape {"projects": {"<name>": {...}}}, this method
		returns the object for the selected project. Otherwise, it returns the input
		mapping itself.

		:param raw: The JSON object that is loaded from the schema file.
		:param project: Optional project name when the schema uses a 'projects' wrapper.
		:return: A mapping of section -> { key → spec }.
		:raises ConfigError: If 'projects' exists, but a project is missing or invalid,
								or if the resolved root is not a mapping.
		"""
		if "projects" in raw:
			if not project:
				raise ConfigError("Schema JSON contains 'projects'; provide project name.")
			projects = raw["projects"]
			if not isinstance(projects, dict) or project not in projects:
				raise ConfigError(f"Project '{project}' not found in JSON schema.")
			root = projects[project]
		else:
			root = raw
		if not isinstance(root, dict):
			raise ConfigError("Schema root must be a JSON object mapping sections.")
		return root

	@staticmethod
	def _schema_parse_to_keyspecs(
			root: Dict[str, Any]
	) -> Tuple[Dict[str, Dict[str, KeySpec]], Dict[str, Dict[str, Any]]]:
		"""
		Convert a schema root object into KeySpecs and collect default values.

		Supported per-key fields:
			- type: str | [str, ...] - see _parse_type_tokens
			- required: bool         - whether the key must be present
			- choices: [...] - optional; restrict allowed values
			- default: any           - optional; default to apply if a key is missing

		:param root: Mapping of section -> { key -> spec }.
		:return: (schema, defaults) where:
				schema   = section -> key -> KeySpec
				defaults = section -> key -> default_value (only for keys that define 'default')
		:raises ConfigError: If the structure is malformed.
		"""
		schema: Dict[str, Dict[str, KeySpec]] = {}
		defaults: Dict[str, Dict[str, Any]] = {}

		for section_name, spec_map in root.items():
			if not isinstance(spec_map, dict):
				raise ConfigError(f"Section '{section_name}' spec must be a JSON object.")

			section_spec: Dict[str, KeySpec] = {}
			section_defaults: Dict[str, Any] = {}

			for key_name, key_spec_dict in spec_map.items():
				if not isinstance(key_spec_dict, dict):
					raise ConfigError(f"Key '{section_name}.{key_name}' spec must be a JSON object.")

				type_field = key_spec_dict.get("type", "str")
				required = bool(key_spec_dict.get("required", False))
				choices = key_spec_dict.get("choices")
				has_default = "default" in key_spec_dict
				default_value = key_spec_dict.get("default")

				expected_type = _parse_type_tokens(type_field)
				validator: Optional[Validator] = None
				if isinstance(choices, list):
					validator = _make_choices_validator(choices)

				key_1 = str(key_name).lower()
				section_spec[key_1] = KeySpec(
					expected_type=expected_type,
					required=required,
					validator=validator,
				)
				if has_default:
					section_defaults[key_1] = default_value

			schema[str(section_name).lower()] = section_spec
			if section_defaults:
				defaults[str(section_name).lower()] = section_defaults

		return schema, defaults

	def _schema_apply_defaults(self) -> None:
		"""
		Apply defaults captured from a previously loaded schema to self._data.

		For each (section, key) with a defined default, if the key is not present in
		the current configuration, the default is assigned. This runs once at
		the beginning of validation.
		"""
		if not getattr(self, "_schema_defaults", None):
			return
		for section_name, pairs in self._schema_defaults.items():
			self._data.setdefault(section_name, {})
			for key_name, default_value in pairs.items():
				if key_name not in self._data[section_name]:
					self._data[section_name][key_name] = default_value
					LOG.debug("default applied: %s.%s = %r", section_name, key_name, default_value)

	def load_schema_from_json(
			self,
			schema_path: Union[str, os.PathLike],
			*,
			template: str,
			project: Optional[str] = None,
			sections: Optional[List[str]] = None,
	) -> Mapping[str, Mapping[str, KeySpec]]:
		"""
		Load a *template* schema (e.g. 'data_handler') and apply it to many sections.

		Accepted shapes:
			1) Direct sections:
				{
					"section": {
						"key": {
							"type": "str|int|list[str]|...", "required": true,
							"choices": [...], "default": <any>
						}
					}
				}
			2) Projected:
				{ "projects": { "<project_name>": { ... same as (1)... } } }

		Defaults (if present) are stored and applied at validate-time.

		:param schema_path: Path to a JSON schema file.
		:param template: Template name to use (e.g., "data_handler").
		:param project: Optional project when using the 'projects' wrapper.
		:param sections: Which sections to apply to; defaults to *all* current sections.
		:return: Per-section schema mapping built from the template.
		:raises ConfigError: On IO/parse errors or shape errors.
		"""
		raw = self._read_json_object(schema_path, "schema JSON")
		# support optional projects wrapper
		root = raw.get("projects", {}).get(project, raw) if "projects" in raw and project else raw
		if not isinstance(root, dict):
			raise ConfigError("Schema root must be a JSON object.")

		template_spec = root.get(template)
		if not isinstance(template_spec, dict):
			raise ConfigError(f"Template '{template}' not found or not an object in schema.")

		target_sections = sections or list(self._data.keys())
		fabricated_root = {sec: template_spec for sec in target_sections}

		schema, defaults = self._schema_parse_to_keyspecs(fabricated_root)
		self._schema_defaults = defaults  # keep for later application
		return schema

	def validate_with_schema_json(
			self,
			schema_path: Union[str, os.PathLike],
			*,
			template: Optional[str] = None,
			project: Optional[str] = None,
			sections: Optional[List[str]] = None
	) -> "RobustConfig":
		"""
		Convenience wrapper: load a *template* schema from JSON and validate.

		:param schema_path: Path to JSON schema file.
		:param template: Template name inside the schema (e.g., "data_handler").
		:param project: Optional project when the schema uses a 'projects' wrapper.
		:param sections: Optional list of section names to apply the template to.
							If None, the template is applied to *all* current sections.
		:return: The self.
		"""
		schema = self.load_schema_from_json(
			schema_path, template=template, project=project, sections=sections
		)
		return self.validate(schema=schema)


# ---------------------- CLI argument parser ------------------------------------
def _basic_sanity_schema(rc: RobustConfig) -> Mapping[str, Mapping[str, KeySpec]]:
	"""
	Build a very generic, inferred validation schema from the *current* data.

	- Includes *all* sections and keys present in rc.to_dict().
	- expected_type is derived from the parsed Python value type.
	- Keys are *not* marked required (profiles may omit keys).
	- Goal: catch obvious type regressions after ENV/CLI overrides/layering.

	NOTE: This is intentionally permissive ane meant for the CLI --validate
	as a quick consistency check. For strict rules, see the
	'validate_with_schema_json' method in the 'RobustConfig' utility class.

	:param rc: Loaded RobustConfig instance.
	:return: Mapping section -> key -> KeySpec.
	"""
	schema: Dict[str, Dict[str, KeySpec]] = {}
	data = rc.to_dict()

	def _infer_expected_type(infer_value: Any) -> Union[type, Tuple[type, ...]]:
		# Lists get validated as 'list' (we don't attempt per-item typing here).
		if isinstance(infer_value, list):
			return (list,)
		# Dicts likewise stay coarse.
		if isinstance(infer_value, dict):
			return (dict,)
		# None stays as NoneType to retain a signal for "maybe missing".
		if infer_value is None:
			return (type(None),)
		# Everything else uses its concrete type (str, int, float, bool, ...).
		return (type(infer_value),)

	for section_name, mapping in data.items():
		spec_for_section: Dict[str, KeySpec] = {}
		for key_name, value in mapping.items():
			spec_for_section[key_name] = KeySpec(
				expected_type=_infer_expected_type(value),
				required=False,
				validator=None,
			)
		schema[section_name] = spec_for_section

	return schema


def _build_arg_parser() -> argparse.ArgumentParser:
	"""
	Build the CLI argument parser for RobustConfig.

	:return: Configured ArgumentParser.
	"""
	p = argparse.ArgumentParser(description="INI configuration utility")

	p.add_argument(
		"-c", "--config", action="append", required=True,
		help="Path to INI file(s) to load. May be provided multiple times for layering.")
	p.add_argument(
		"--csv-delimiters", default=None,
		help="Optional delimiters for splitting plain strings (e.g. ',;\\t ')."
	)
	p.add_argument(
		"--dump", choices=["pretty", "json"], default="pretty", help="Output format for dump."
	)
	p.add_argument(
		"--env-prefix", default="CONF",
		help="Environment variable prefix for overrides (default: CONF)."
	)
	p.add_argument(
		"--interpolation", choices=["extended", "none"], default="extended",
		help="Interpolation mode for INI files (default: extended). Use 'none' if your values contain $."
	)
	p.add_argument(
		"--log-file", default=None,
		help="Path to logfile (default: ./utilities/logs/robust_config.log)."
	)
	p.add_argument(
		"--list-sections", action="store_true", help="List sections and exit."
	)
	p.add_argument(
		"--log-level", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
		default=None, help="Set log level just for this run."
	)
	p.add_argument(
		"--no-file-log", action="store_true",
		help="Disable writing logs to a file"
	)
	p.add_argument(
		"-o", "--override", action="append", default=[], help="Override as section.key=value (may repeat)."
	)
	p.add_argument(
		"-p", "--print-section", dest="print_section", default=None,
		help="Print only the given section and exit (overrides --sections)."
	)
	p.add_argument(
		"--sections", nargs="*", default=None, help="Sections to include (default: all).")
	p.add_argument(
		"--schema-apply", default="*",
		help="Comma-separated sections to apply the template to, or '*' for all sections (default '*')."
	)
	p.add_argument(
		"--schema-json", default=None, help="Path to a JSON schema file to validate against."
	)
	p.add_argument(
		"--schema-project", default=None,
		help="Project name inside the schema JSON (when using 'projects' root)."
	)
	p.add_argument(
		"--schema-template", default=None,
		help="Treat the schema JSON as a template (e.g., 'data_handler') to apply to many sections."
	)
	p.add_argument(
		"--validate", action="store_true", help="Run a basic sanity validation."
	)
	return p


def main(argv: Optional[List[str]] = None) -> int:
	"""
	Entrypoint for the command-line interface.

	It loads INI files, applies ENV/CLI overrides, optionally validates,
	and prints either the section list or a dump in the requested format.

	:param argv: Optional argv list for testing; defaults to sys.argv[1: ].
	:return: Process exit code (0=OK, 2=ConfigError, 1=unexpected error).
	"""
	parser = _build_arg_parser()
	args = parser.parse_args(argv)
	if args.schema_json and not args.validate:
		args.validate = True

	# On-demand long lever override
	if args.log_level:
		LOG.setLevel(getattr(logging, args.log_level))

	if not getattr(args, "no_file_log", False):
		# if user didn't pass --log-file, enable_file_logging will default to logs/robust_config.log
		enable_file_logging(
			log_path=getattr(args, "log_file", None),
			level=args.log_level or LOG.level,
			overwrite=True
		)

	# ensure even uncaught exceptions are recorded
	install_global_exception_logging()

	try:
		rc = RobustConfig(
			env_prefix=args.env_prefix,
			csv_delimiters=args.csv_delimiters,
			interpolation=args.interpolation,
		).load(args.config).apply_env_overrides().apply_overrides(args.override)

		if args.list_sections:
			for name in sorted(rc.to_dict()):
				print(name)
			return 0

		if args.print_section:
			print(rc.dump(fmt=args.dump, sections=[args.print_section]))
			return 0

		if args.validate:
			if args.schema_json:
				if args.schema_template:
					sections_to_apply = None if args.schema_apply.strip() == "*" \
						else [s.strip() for s in args.schema_apply.split(",") if s.strip()]
					schema = rc.load_schema_from_json(
						args.schema_json,
						template=args.schema_template,
						project=args.schema_project,
						sections=sections_to_apply
					)
					rc.validate(schema=schema)
				else:
					rc.validate_with_schema_json(
						args.schema_json,
						project=args.schema_project
					)
			else:
				rc.validate(schema=_basic_sanity_schema(rc))

			LOG.info("Validation OK")
			print("Validation OK")
			if not (args.sections or args.print_section or args.list_sections):
				return 0

		# Dump (entire config or selected sections)
		print(rc.dump(fmt=args.dump, sections=args.sections))
		return 0

	except ConfigError as exc:
		LOG.exception("Configuration error: %s", exc)
		return 2
	except Exception as exc:
		LOG.exception(f"Unexpected error:{exc}")
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
