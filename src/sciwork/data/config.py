# src/sciwork/data/config.py

"""Configuration helpers for :class:`sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from ..config import bootstrap_json_file
from ..config import store, templates
from ..logutil import get_logger

LOG = get_logger(__name__)

_CONFIG_SCHEMA_FILENAME = "data_handler_schema.json"
_CONFIG_INI_FILENAME = "data_handler.ini"

_DATA_HANDLER_SCHEMA: Dict[str, Dict[str, Dict[str, object]]] = {
	"data_handler": {
		"data_folderpath": {"type": "str", "required": True},
		"general_keywords": {"type": "str", "default": ""},
		"general_antikeywords": {"type": "str", "default": ""},
		"keywords": {"type": "str", "default": ""},
		"antikeywords": {"type": "str", "default": ""},
		"header_rows": {"type": "str", "default": ""},
		"sheet_names": {"type": "str", "default": ""},
	}
}

_INI_HEADER = """SciWork DataHandler configuration

Fill in dataset specific filters below. Multiple keyword sets are separated by semicolons
and individual keywords by commas, matching the legacy utility format.
"""


@dataclass
class FilterSetConfig:
	"""Keyword/metadata configuration for a single dataset group."""

	name: str
	keywords: Tuple[str, ...] = field(default_factory=tuple)
	antikeywords: Tuple[str, ...] = field(default_factory=tuple)
	header_row: Optional[int] = None
	sheet_name: Optional[str] = None


@dataclass
class DataHandlerConfig:
	"""Structured configuration parsed from INI/CLI parameters."""

	data_folderpath: Path
	general_keywords: Tuple[str, ...]
	general_antikeywords: Tuple[str, ...]
	sets: Tuple[FilterSetConfig, ...]

	@staticmethod
	def _split_csv(value: str, *, sep: str = ",") -> Tuple[str, ...]:
		items = [chunk.strip() for chunk in value.split(sep)] if value else []
		filtered = [item for item in items if item]
		unique_ordered = list(dict.fromkeys(filtered))
		return tuple(unique_ordered)

	@staticmethod
	def _split_optional(value: str, *, sep: str = ";") -> Tuple[Optional[str], ...]:
		if not value:
			return tuple()
		parts = [chunk.strip() or None for chunk in value.split(sep)]
		return tuple(parts)

	@classmethod
	def from_strings(
			cls,
			*,
			data_folderpath: str,
			general_keywords: str = "",
			general_antikeywords: str = "",
			keywords: str = "",
			antikeywords: str = "",
			header_rows: str = "",
			sheet_names: str = ""
	) -> "DataHandlerConfig":
		"""Parse the legacy comma/semicolon separated strings."""

		general_kw = cls._split_csv(general_keywords)
		general_akw = cls._split_csv(general_antikeywords)

		set_keywords = cls._split_optional(keywords, sep=";")
		set_antikeywords = cls._split_optional(antikeywords, sep=";")
		set_headers = cls._split_optional(header_rows, sep=";")
		set_sheets = cls._split_optional(sheet_names, sep=";")

		max_len = max(len(set_keywords), len(set_antikeywords), 1)
		if not set_keywords:
			set_keywords = tuple(
				",".join(general_kw) if general_kw else "" for _ in range(max_len)
			)
		if not set_antikeywords:
			set_antikeywords = tuple(
				",".join(general_akw) if general_akw else "" for _ in range(max_len)
			)

		def _ensure_length(items: Tuple[Optional[str], ...]) -> Tuple[Optional[str], ...]:
			if not items:
				return tuple(None for _ in range(max_len))
			if len(items) >= max_len:
				return items
			last = items[-1] if items else None
			return items + tuple(last for _ in range(max_len - len(items)))

		set_headers = _ensure_length(set_headers)
		set_sheets = _ensure_length(set_sheets)

		filter_sets: List[FilterSetConfig] = []
		for idx in range(max_len):
			raw_kw = set_keywords[idx] if idx < len(set_keywords) else None
			raw_akw = set_antikeywords[idx] if idx < len(set_antikeywords) else None
			header = set_headers[idx]
			sheet = set_sheets[idx]

			kw = cls._split_csv(raw_kw or "") if raw_kw not in (None, "") else general_kw
			akw = cls._split_csv(raw_akw or "") if raw_akw not in (None, "") else general_akw
			if header not in (None, ""):
				try:
					header_int = int(header)
				except (TypeError, ValueError) as exc:
					raise ValueError(f"Header row must be an integer: {header}") from exc
			else:
				header_int = None
			filter_sets.append(
				FilterSetConfig(
					name=f"Set {idx}",
					keywords=kw or general_kw,
					antikeywords=akw or general_akw,
					header_row=header_int,
					sheet_name=sheet or None
				)
			)

		return cls(
			data_folderpath=Path(data_folderpath).expanduser(),
			general_keywords=general_kw,
			general_antikeywords=general_akw,
			sets=tuple(filter_sets)
		)

	def iter_sets(self) -> Iterator[FilterSetConfig]:
		"""Yield filter set definitions in configured order."""
		return iter(self.sets)


def bootstrap_data_handler_config(
		*,
		prefer: str = "project",
		overwrite_schema: bool = False,
		overwrite_ini: bool = False,
		sections: Optional[Iterable[str]] = None,
) -> Tuple[Path, Path]:
	"""Ensure both schema JSON and INI template exist for the data handler."""

	schema_path = bootstrap_json_file(
		name=_CONFIG_SCHEMA_FILENAME,
		payload=_DATA_HANDLER_SCHEMA,
		prefer=prefer,  # type: ignore[arg-type]
		overwrite=overwrite_schema
	)

	section_names = list(sections) if sections else ["data"]
	ini_path = store.resolve_config_path(
		_CONFIG_INI_FILENAME,
		prefer=prefer,  # type: ignore[arg-type]
	)

	if overwrite_ini or not ini_path.exists():
		templates.write_ini_from_template(
			schema_json_path=schema_path,
			dest_path=ini_path,
			template="data_handler",
			sections=section_names,
			include_defaults=True,
			placeholder="",
			header_comment=_INI_HEADER,
			overwrite=True
		)
		LOG.info("Created data handler INI template at %s", ini_path)
	else:
		LOG.info("INI template already present at %s", ini_path)

	return schema_path, ini_path
