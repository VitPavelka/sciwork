# src/sciwork/fs/loaders.py

from __future__ import annotations

from typing import Any, Optional

from ..logutil import get_logger
from .base import PathLike, PathOpsBase
from .classify import Classify
from .loaders_base import BaseLoaders

LOG = get_logger(__name__)

__all__ = ["Load"]


class Load(PathOpsBase, Classify, BaseLoaders):
	"""
	Facade that provides :meth:`any_data_loader` on top of concrete loaders.

	This class relies on other mixins present in your project:

	- ``PathOpsBase`` for path resolution (``_abs``) and base_dir handling
	- a classifier method ``classify_path(path) -> str`` (e.g., 'comma_separated_values', 'text_only', ...)
	- encoding/delimiter helpers: ``detect_encoding`` and ``detect_delimiter``

	If your current ``PathOps`` already mixes these in, you can inherit:
	"""
	def any_data_loader(
			self,
			path: PathLike,
			*,
			# common options; loaders pick what they need
			sheet_name: Optional[str] = None,  # for Excel; 'choice' → prompt
			encoding: Optional[str] = None,  # for text files
			delimiter: Optional[str] = None,  # for CSV/TXT
			header: Optional[int] = None,
			dtype: Optional[dict] = None,
			include_hidden_rows: bool = False,  # for Excel via openpyxl
			force_type: Optional[str] = None
	) -> Any:
		"""
		Open a variety of data files and return either a DataFrame or Python data structures.

		Supported:
			- Excel (.xlsx, .xlsm, .xls)    → pandas.DataFrame (optionally skip rows)
			- CSV/TSV/Text (.csv/.tsv/.txt) → pandas.DataFrame (delimiter detection when missing)
			- JSON (.json)                  → dict/list (returned as loaded Python objects)
			- XML (.xml)                    → pandas.DataFrame (flat dict per element)
			- SIF (.sif)                    → pandas.DataFrame (via :meth:`_load_sif`)

		:param path: Input file path.
		:param sheet_name: For Excel: sheet name to load. If 'choice', the user is prompted to pick.
							If None, the first sheet is used.
		:param encoding: Encoding for text files; auto-detected if None.
		:param delimiter: Delimiter for CSV/TXT; auto-detected if None.
		:param header: Header row index (0-based) for tabular readers.
		:param dtype: Optional dtype mapping passed to the pandas readers.
		:param include_hidden_rows: If True, Excel reader includes rows even if hidden.
									If False, hidden rows are skipped (via openpyxl).
		:param force_type: Force a specific type_label (bypasses classification).
		:return: DataFrame or Python object depending on format.
		:raises FileNotFoundError: Source not found.
		:raises ValueError: For unsupported/unknown types.
		"""
		p = self._abs(path)
		if not p.exists():
			raise FileNotFoundError(f"File '{p}' not found")

		kind = force_type or self.classify_path(p)

		# Excel
		if kind in {"ms_excel_spreadsheet", "excel", "xlsx",  "xls", "xlsm"}:
			return self._load_ms_excel_spreadsheet(
				p, sheet_name=sheet_name, header=header, dtype=dtype, include_hidden_rows=include_hidden_rows
			)

		# CSV/TSV
		if kind in {"comma_separated_values", "csv", "tsv"}:
			return self._load_csv(
				p, encoding=encoding, delimiter=delimiter, header=header, dtype=dtype,
			)

		# Generic delimited text
		if kind in {"text_only", "txt", "log"}:
			return self._load_text_only(
				p, encoding=encoding, delimiter=delimiter, header=header, dtype=dtype
			)

		# JSON
		if kind in {"javascript_object_notation", "json"}:
			return self._load_json(p)

		# XML
		if kind in {"extensible_markup_language", "xml"}:
			return self._load_xml(p)

		# SIF
		if kind in {"andor_scientific_image_format", "sif"}:
			return self._load_sif(p)

		# UV/VIS SPC
		if kind in {"uv_vis_spectrum_spc", "spc"}:
			from .parsers.uvvis_spc import load_uvvis_spc
			return load_uvvis_spc(p)

		if kind == "folder":
			raise ValueError(f"Expected a file, got folder: {p}")

		raise ValueError(f"Unsupported/unknown file type: {p.suffix.lower() or '<no extension>'}")
