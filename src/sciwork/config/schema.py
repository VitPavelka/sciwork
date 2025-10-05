# src/sciwork/config/schema.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from .loader import ConfigError

Validator = Callable[[Any], None]
PathLike = Union[str, Path]


# ------------------------------- KeySpec -----------------------------------
@dataclass
class KeySpec:
    """
    Specification for a configuration key used during validation.

    :param expected_type: Allowed type (or tuple of types) for the key's value.
                          Use Python types (e.g., ``str``, ``int``, ``list``) or
                          a tuple like ``(int, type(None))`` to allow ``None``.
    :param required: Whether the key must be present in the section.
    :param validator: Optional callable that receives the *parsed* value and
                      must raise on invalid content.
    """
    expected_type: Union[type, Tuple[type, ...]]
    required: bool = False
    validator: Optional[Validator] = None

    def __post_init__(self) -> None:
        if self.validator is not None and not callable(self.validator):
            raise TypeError("KeySpec.validator must be callable or None")


# ------------------------------- Type parsing -------------------------------
_TYPE_MAP: Dict[str, type] = {
    # primitives
    "str": str, "string": str,
    "int": int, "integer": int,
    "float": float, "number": float,
    "bool": bool, "boolean": bool,
    "null": type(None), "none": type(None),
    # containers
    "list": list, "array": list,
    "dict": dict, "object": dict,
}


def _parse_type_tokens(type_field: Union[str, List[Optional[str]]]) -> Tuple[type, ...]:
    """
    Convert a type descriptor into a tuple of Python types for KeySpec.expected_type.

    Supported tokens (case-insensitive):
      - primitives: ``"str"``, ``"int"``, ``"float"``, ``"bool"``, ``"null"`` (or ``"none"``)
      - containers: ``"list"``, ``"dict"``
      - parametric list: ``"list[str]"`` etc. → treated as ``list`` for *expected_type*
      - union: a JSON list like ``["int", "null"]``

    Unknown tokens degrade gracefully to ``str`` (so validation still works).

    :param type_field: String token (e.g., ``"str"``) or a list of tokens
                       (e.g., ``["int", "null"]``). Items may be ``null`` in JSON.
    :return: Tuple of acceptable Python types (e.g., ``(int, type(None))``).
    """
    def _one(token: Optional[str]) -> type:
        if token is None:
            return type(None)
        t = token.strip().lower()
        if t.startswith("list[") and t.endswith("]"):
            return list
        return _TYPE_MAP.get(t, str)

    if isinstance(type_field, str):
        return (_one(type_field),)
    return tuple(_one(tok) for tok in type_field)


# ----------------------------- Choices validator ----------------------------
def make_choices_validator(choices: Iterable[Any]) -> Validator:
    """
    Build a validator that ensures the value is one of the allowed *choices*.

    :param choices: Iterable of allowed values (compared using equality).
    :return: A callable that raises ``ValueError`` if the value is not allowed.
    """
    allowed = set(choices)

    def _validator(value: Any) -> None:
        if value not in allowed:
            raise ValueError(f"value {value!r} not in allowed set {sorted(allowed)!r}")

    return _validator


# -------------------------- JSON schema ingestion ---------------------------
def _read_json_object(path_like: PathLike, what: str) -> Dict[str, Any]:
    """
    Load a JSON file and ensure the top-level is an object.

    :param path_like: Path to the JSON file.
    :param what: Human label used in error messages (e.g., ``"schema JSON"``).
    :return: Parsed top-level object.
    :raises ConfigError: On IO/parse errors or when the JSON is not an object.
    """
    path = Path(path_like)
    if not path.exists():
        raise ConfigError(f"Missing {what}: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception as exc:
        raise ConfigError(f"Failed reading {what} '{path}': {exc}") from exc
    if not isinstance(obj, dict):
        raise ConfigError(f"{what} must be a JSON object.")
    return obj


def schema_parse_to_keyspecs(root: Mapping[str, Mapping[str, Any]]
                             ) -> Tuple[Dict[str, Dict[str, KeySpec]], Dict[str, Dict[str, Any]]]:
    """
    Convert a *schema root* mapping into (KeySpec mapping, default mapping).

    Expected per-key spec shape (all fields optional unless noted):
      ... code-block:: JSON

         {
           "type": "str | int | float | bool | null | list | dict | list[str] | ...",
           "required": true,
           "choices": ["foo", "bar", 10, null],
           "default": <any JSON value>
         }

    Notes
    -----
    * ``type`` may be a string or a list (logical OR). Parametric lists like
      ``"list[str]"`` are accepted, but the expected type is just ``list``; element
      typing is out of scope for this straightforward validator.
    * When the `` choices `` parameter is given, a validator checking membership is attached.
    * ``default`` values are collected separately and *not* applied here.

    :param root: Mapping of ``section -> mapping(key -> spec)``.
    :return: ``(schema, defaults)`` where:
             - ``schema`` is ``Dict[section][key] -> KeySpec``
             - ``defaults`` param is ``Dict[section][key] -> value`` (only keys with defaults)
    :raises ConfigError: On invalid shapes or unsupported field types.
    """
    schema: Dict[str, Dict[str, KeySpec]] = {}
    defaults: Dict[str, Dict[str, Any]] = {}

    for section_name, spec_map in root.items():
        if not isinstance(spec_map, Mapping):
            raise ConfigError(f"Section '{section_name}' spec must be a mapping.")
        sec = str(section_name).lower()
        sec_schema: Dict[str, KeySpec] = {}
        sec_defaults: Dict[str, Any] = {}

        for key_name, key_spec in spec_map.items():
            if not isinstance(key_spec, Mapping):
                raise ConfigError(f"Key '{section_name}.{key_name}' spec must be a mapping.")

            # type
            type_field = key_spec.get("type", "str")
            expected_type = _parse_type_tokens(type_field)

            # required
            required = bool(key_spec.get("required", False))

            # validator via choices (if present)
            validator: Optional[Validator] = None
            if "choices" in key_spec:
                choices = key_spec.get("choices", [])
                if not isinstance(choices, (list, tuple, set)):
                    raise ConfigError(f"'choices' for '{section_name}.{key_name}' must be an array")
                validator = make_choices_validator(choices)

            # assemble KeySpec
            kn = str(key_name).lower()
            sec_schema[kn] = KeySpec(expected_type=expected_type, required=required, validator=validator)

            # default (optional)
            if "default" in key_spec:
                sec_defaults[kn] = key_spec.get("default", None)

        schema[sec] = sec_schema
        if sec_defaults:
            defaults[sec] = sec_defaults

    return schema, defaults


def load_schema_from_json(path: PathLike) -> Dict[str, Dict[str, Any]]:
    """
    Load a schema JSON file and return its top-level object.

    This does not perform any transformation; it is a thin convenience wrapper
    for :func:`_read_json_object`.

    :param path: Path to JSON schema.
    :return: Top-level JSON object.
    :raises ConfigError: On IO/parse errors or invalid top-level type.
    """
    return _read_json_object(path, "schema JSON")


def load_schema_template_from_json(
    path: PathLike,
    *,
    template: str,
    project: Optional[str] = None,
    sections: Optional[List[str]] = None,
) -> Tuple[Dict[str, Dict[str, KeySpec]], Dict[str, Dict[str, Any]]]:
    """
    Load a *template* schema (e.g. ``"data_handler"``) and apply it to many sections.

    Accepted JSON shapes:
      1) Direct sections (no wrapper):
         ... code-block:: JSON

            {
              "data_handler": { "...": { "type": "str", "required": true } }
            }

      2) With project wrapper:
         ... code-block:: JSON

            {
              "projects": {
                "my_project": {
                  "data_handler": { "...": { "type": "str" } }
                }
              }
            }

    The selected template (``template``) is *replicated* for each section name in
    ``sections``. If ``sections`` is omitted, the function uses an empty list and
    still returns parsed ``(schema, defaults)`` for possible later application.

    :param path: Path to the schema JSON.
    :param template: Template object name to use (e.g., ``"data_handler"``).
    :param project: Optional project name when using a ``"projects"`` wrapper.
    :param sections: Section names to which to apply the template; if ``None``,
                     an empty list is assumed (you can still use the returned
                     template schema to apply later).
    :return: ``(schema, defaults)`` for the fabricated root.
    :raises ConfigError: On missing template or invalid shapes.
    """
    raw = load_schema_from_json(path)

    # Optional projects wrapper
    if "projects" in raw:
        projs = raw.get("projects")
        if not isinstance(projs, Mapping):
            raise ConfigError("'projects' in schema must be an object")
        if project is None:
            # You may choose to raise here instead; we keep it permissive.
            root = projs
        else:
            root = projs.get(project, {})
            if not isinstance(root, Mapping):
                raise ConfigError(f"Project '{project}' not found in schema or invalid type")
    else:
        root = raw

    if not isinstance(root, Mapping):
        raise ConfigError("Schema root must be a JSON object.")

    template_spec = root.get(template)
    if not isinstance(template_spec, Mapping):
        raise ConfigError(f"Template '{template}' not found or not an object in schema.")

    target_sections = sections or []
    fabricated_root: Dict[str, Dict[str, Any]] = {sec: template_spec for sec in target_sections}

    if not fabricated_root:
        return {}, {}

    return schema_parse_to_keyspecs(fabricated_root)


# ---------------------------- Defaults + validate ---------------------------
def apply_defaults(data: Dict[str, Dict[str, Any]],
                   defaults: Mapping[str, Mapping[str, Any]]) -> None:
    """
    Apply per-section defaults into *data* for keys that are missing.

    :param data: Configuration values (modified in place).
    :param defaults: Mapping ``section -> key -> default_value``.
    """
    for sec, mapping in defaults.items():
        if not isinstance(mapping, Mapping):
            continue
        bucket = data.get(sec)
        if bucket is None:
            continue
        for key, dval in mapping.items():
            if key not in bucket:
                bucket[key] = dval


def validate_data(data: Mapping[str, Mapping[str, Any]],
                  schema: Mapping[str, Mapping[str, KeySpec]]) -> None:
    """
    Validate presence, types, and custom constraints for *data*.

    For each section defined in *schema* the validator checks:
      * missing required keys,
      * ``isinstance(value, expected_type)`` for present keys,
      * runs optional ``validator(value)``.

    All problems are aggregated and raised together as ``ConfigError``.

    :param data: Parsed configuration values (``section -> key -> value``).
    :param schema: Validation schema (``section -> key -> KeySpec``).
    :raises ConfigError: When any validation error occurs.
    """
    errors: List[str] = []

    for section_name, key_specs in (schema or {}).items():
        values = data.get(section_name, {}) or {}
        for key_name, spec in key_specs.items():
            # required?
            if spec.required and key_name not in values:
                errors.append(f"[{section_name}] missing required key '{key_name}'")
                continue
            if key_name not in values:
                continue

            value = values[key_name]
            if not isinstance(value, spec.expected_type):
                errors.append(
                    f"[{section_name}] key '{key_name}' expected {spec.expected_type}, "
                    f"got {type(value)} ({value!r})"
                )
                continue

            if spec.validator is not None:
                try:
                    spec.validator(value)
                except Exception as exc:
                    errors.append(f"[{section_name}] key '{key_name}' failed validation: {exc}")

    if errors:
        hint = "Tip: pretty-print your loaded config to inspect values and fix the configuration."
        raise ConfigError("\n".join(errors) + "\n\n" + hint)


__all__ = [
    "KeySpec",
    "Validator",
    "_parse_type_tokens",
    "make_choices_validator",
    "schema_parse_to_keyspecs",
    "load_schema_from_json",
    "load_schema_template_from_json",
    "apply_defaults",
    "validate_data",
]
