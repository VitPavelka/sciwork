from __future__ import annotations

import ast
import json
import logging
import configparser

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union

LOG = logging.getLogger(__name__)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ConfigError(Exception):
	"""
    Generic configuration error used by loader utilities.

    This module defines its own exception to avoid circular imports.
    A package-level errors.py can later centralize this if desired.
    """


# ---------------------------------------------------------------------------
# Helpers: interpolation, parsing, merging
# ---------------------------------------------------------------------------
def choose_interpolation(interpolation: Optional[str]) -> Optional[configparser.Interpolation]:
	"""
    Return an interpolation object for configparser based on a textual flag.

    If *interpolation* is one of {"none","no","off","false","f","raw"}, the interpolation
    is disabled (returns None). Otherwise, ExtendedInterpolation is used.

    :param interpolation: Text flag controlling interpolation behavior.
    :return: Interpolation object or None.
    """
	if interpolation is None:
		return configparser.ExtendedInterpolation()
	flag = str(interpolation).lower().strip()
	if flag in {"none", "no", "off", "false", "f", "raw"}:
		return None
	return configparser.ExtendedInterpolation()


def _split_csv(text: str, delimiters: Optional[Union[str, Iterable[str]]]) -> List[str]:
	"""
    Split *text* by a set of single-character delimiters, respecting quotes and escapes.

    Supports both single and double quotes and the backslash escape inside quoted parts.
    Delimiters must be single characters (e.g. ',', ';', '\\t', ' ').

    :param text: Input string to split.
    :param delimiters: Either a string of delimiter characters or an iterable of
                       single-character strings. If None, no splitting is performed.
    :return: List of token strings (untrimmed; caller may strip/parse further).
    """
	if not delimiters:
		return [text]

	if isinstance(delimiters, str):
		delims = set(delimiters)
	else:
		delims = set()
		for d in delimiters:
			if not isinstance(d, str) or len(d) != 1:
				raise ValueError("Only single-character delimiters are supported.")
			delims.add(d)

	out: List[str] = []
	buf: List[str] = []
	quote: Optional[str] = None
	i = 0
	while i < len(text):
		ch = text[i]
		if quote:
			if ch == "\\" and i + 1 < len(text):
				buf.append(text[i + 1])
				i += 2
				continue
			if ch == quote:
				quote = None
			else:
				buf.append(ch)
		else:
			if ch in {"'", '"'}:
				quote = ch
			elif ch in delims:
				out.append("".join(buf))
				buf.clear()
			else:
				buf.append(ch)
		i += 1
	out.append("".join(buf))
	return out


def parse_value(raw: str, *, csv_delimiters: Optional[Union[str, Iterable[str]]] = None) -> Any:
	"""
    Parse a raw INI string into a typed Python value.

    The parser attempts, in order:
      1) ``ast.literal_eval`` for safe Python literals (numbers, strings, lists, dicts, booleans, None).
      2) Common textual None markers: ``none``, ``null``, ``na``, ``n/a``.
      3) Booleans: ``true/yes/on`` → ``True``, ``false/no/off`` → ``False``.
      4) CSV-like splitting **only if** ``csv_delimiters`` is provided (items parsed recursively).
      5) Numeric fallback (int/float).
      6) Otherwise the original string.

    :param raw: Source text as read from ConfigParser.
    :param csv_delimiters: Optional set of single-char delimiters to enable CSV splitting.
    :return: Best-effort typed value.
    """
	s = raw.strip()

	# 1) Safe Python literals
	try:
		value = ast.literal_eval(s)
		# Normalize tuples to lists for config friendliness
		if isinstance(value, tuple):
			return list(value)
		return value
	except Exception:
		pass

	# 2) None-like markers
	lower = s.lower()
	if lower in {"none", "null", "na", "n/a"}:
		return None

	# 3) Booleans
	if lower in {"true", "yes", "on"}:
		return True
	if lower in {"false", "no", "off"}:
		return False

	# 4) CSV only when explicitly enabled
	if csv_delimiters and any(
			d in s for d in (csv_delimiters if isinstance(csv_delimiters, str) else list(csv_delimiters))):
		parts = _split_csv(s, csv_delimiters)
		# avoid infinite recursion: subitems are parsed with CSV disabled
		return [parse_value(p.strip(), csv_delimiters=None) for p in parts]

	# 5) Numbers
	try:
		if "." in s:
			return float(s)
		return int(s)
	except ValueError:
		# 6) String fallback
		return s


def merge_layer(base: MutableMapping[str, Dict[str, Any]], layer: Mapping[str, Mapping[str, Any]]) -> None:
	"""
	Deep-merge *layer* into *base* at the section/key level.

	Later (right) values overwrite earlier (left) values for identical keys.

	:param base: Destination mapping (modified in place).
	:param layer: Source mapping to overlay.
	"""
	for sec, mapping in layer.items():
		if not isinstance(mapping, Mapping):
			raise ConfigError(f"Section '{sec}' must be a mapping, got {type(mapping).__name__}.")
		dest = base.setdefault(sec, {})
		for k, v in mapping.items():
			dest[k] = v


def merge_dicts(base: MutableMapping[str, Dict[str, Any]], *layers: Mapping[str, Mapping[str, Any]]) -> MutableMapping[
	str, Dict[str, Any]]:
	"""
	Deep-merge one or more *layers* into *base* at section/key granularity.

	Later layers overwrite earlier ones for identical keys.

	:param base: Destination mapping (modified in place).
	:param layers: One or more mappings to overlay.
	:return: The mutated *base* (for chaining).
	"""
	for layer in layers:
		merge_layer(base, layer)
	return base


# ---------------------------------------------------------------------------
# INI loading
# ---------------------------------------------------------------------------
def _cp_to_typed_dict(cp: configparser.ConfigParser, *, csv_delimiters: Optional[Union[str, Iterable[str]]] = None) -> \
		Dict[str, Dict[str, Any]]:
	"""
	Project a ConfigParser into a nested dict with parsed value types.

	:param cp: Prepared ConfigParser (already read).
	:param csv_delimiters: Optional CSV delimiters for value parsing.
	:return: Dict[section]->Dict[key->typed value] (lowercased section/key names).
	"""
	out: Dict[str, Dict[str, Any]] = {}
	for section in cp.sections():
		sec_name = section.lower()
		dest: Dict[str, Any] = {}
		for key, value in cp.items(section):
			dest[key.lower()] = parse_value(value, csv_delimiters=csv_delimiters)
		out[sec_name] = dest
	return out


def _resolve_inheritance(data: MutableMapping[str, Dict[str, Any]]) -> None:
	"""
    Support ``extends`` key in sections to mix in parent keys (shallow merge per level).

    Example:
        [dev]
        extends = base, other

    :param data: Dict of sections to resolve (modified in place).
    :raises ConfigError: When a referenced parent section does not exist.
    """
	visited: Dict[str, bool] = {}

	def merge_chain(section: str) -> Dict[str, Any]:
		if section in visited:
			return data.get(section, {})
		visited[section] = True

		current = data.get(section, {})
		parents_raw = current.get("extends")
		if not parents_raw:
			return current

		parents = parents_raw if isinstance(parents_raw, list) else [parents_raw]
		merged: Dict[str, Any] = {}
		for parent in parents:
			parent_name = str(parent).lower()
			if parent_name not in data:
				raise ConfigError(f"[{section}] extends unknown section '{parent_name}'")
			merged.update(merge_chain(parent_name))
		# overlay current (without the 'extends' key)
		merged.update({k: v for k, v in current.items() if k != "extends"})
		data[section] = merged
		return merged

	for sec in list(data.keys()):
		merge_chain(sec)


def load_ini_files(files: Iterable[PathLike],
                   *,
                   interpolation: Optional[str] = "extended",
                   csv_delimiters: Optional[Union[str, Iterable[str]]] = None) -> Tuple[
	Dict[str, Dict[str, Any]], List[Path]]:
	"""
    Load one or more INI files and return a typed, merged mapping of sections.

    Later files override earlier ones (ConfigParser layering). Values are parsed to
    Python types via :func:`parse_value`. Sections support inheritance via the
    ``extends`` key (resolved after reading all files).

    :param files: Iterable of INI file paths.
    :param interpolation: Text flag to control interpolation ('extended' or 'none' etc.).
    :param csv_delimiters: Optional CSV delimiters to enable CSV-like value parsing.
    :return: (data, loaded_files)
    :raises ConfigError: On missing file(s) or IO errors.
    """
	paths = [Path(p) for p in files]
	missing = [str(p) for p in paths if not p.exists()]
	if missing:
		raise ConfigError(f"Missing config file(s): {', '.join(missing)}")

	cp = configparser.ConfigParser(interpolation=choose_interpolation(interpolation))
	loaded: List[Path] = []

	for p in paths:
		try:
			with p.open("r", encoding="utf-8") as fh:
				cp.read_file(fh)
			loaded.append(p)
			LOG.info("Loaded INI file: %s", p)
		except Exception as exc:
			raise ConfigError(f"Failed reading '{p}': {exc}") from exc

	data = _cp_to_typed_dict(cp, csv_delimiters=csv_delimiters)
	_resolve_inheritance(data)
	return data, loaded


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------
def load_json_files(files: Iterable[PathLike]) -> Dict[str, Dict[str, Any]]:
	"""
    Load and merge multiple JSON config files into a single mapping.

    Each JSON file must be a top-level object with the shape:
        { "section": { "key": value, ... }, ... }

    Later files override earlier ones at section/key granularity.

    :param files: Iterable of JSON paths.
    :return: Merged mapping.
    :raises ConfigError: On IO/parse errors or invalid shapes.
    """
	merged: Dict[str, Dict[str, Any]] = {}
	for path_like in files:
		p = Path(path_like)
		if not p.exists():
			raise ConfigError(f"Missing JSON config file: {p}")
		try:
			with p.open("r", encoding="utf-8") as fh:
				obj = json.load(fh)
		except Exception as exc:
			raise ConfigError(f"Failed reading JSON '{p}': {exc}") from exc

		if not isinstance(obj, dict):
			raise ConfigError(f"Top-level JSON in '{p}' must be an object.")

		# Normalize section/key names to the lowercase
		lowered: Dict[str, Dict[str, Any]] = {}
		for sec, mapping in obj.items():
			if not isinstance(mapping, dict):
				raise ConfigError(f"Section '{sec}' in '{p}' must be an object.")
			lowered[sec.lower()] = {str(k).lower(): v for k, v in mapping.items()}

		merge_layer(merged, lowered)
		LOG.info("Merged JSON file: %s", p)
	return merged


__all__ = [
	"ConfigError",
	"choose_interpolation",
	"parse_value",
	"merge_layer",
	"merge_dicts",
	"load_ini_files",
	"_resolve_inheritance",  # exported for testing, keep private by convention if you prefer
	"load_json_files"
]
