# src/sciwork/fs/loaders_base.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Iterable
import json

from ..logutil import get_logger
from .encoding import Encoding
from ..imports import openpyxl, ET
from ..imports import pandas as pd, sif_parser as sif

LOG = get_logger(__name__)

__all__ = ["BaseLoaders"]


class BaseLoaders(Encoding):
	"""
	Mixin with concrete data-file loaders.
	Heavy deps are imported lazily in helpers.
	"""
	# --- Helpers ---
	@staticmethod
	def _normalize_delim(value: Optional[str]) -> Optional[str]:
		"""Turn literal ``'\\t'`` into a tab character; pass others through."""
		if value is None:
			return None
		return "\t" if value == "\\t" else value

	@staticmethod
	def _ask_choice_number(title: str, items: Iterable[str]) -> int:
		"""
		Ask the user to pick 1…N. Uses ``self.prompter`` if present, else `input()`.
		:return: 1-based index.
		"""
		try:
			from ..console.prompter import Prompter
			prompter = Prompter()
		except Exception:
			LOG.info("'BaseLoaders._ask_choice_number' method runs without the optional dependency 'sciwork.console.prompter.Prompter'.")
			prompter = None

		items = list(items)
		lines = [title] + [f"{i+1}: {name}" for i, name in enumerate(items)] + [""]

		if prompter is not None:
			prompter.print_lines(lines)
		else:
			print([f"{line}\n" for line in lines])

		def _validate(s: str) -> None:
			try:
				i = int(s)
				if not (1 <= i <= len(items)):
					raise ValueError
			except Exception:
				raise ValueError("Enter a number between 1 and %d" % len(items))

		msg = f" Select [1..{len(items)}]: "
		if prompter is not None:
			choice = prompter.prompt(msg, validate=_validate, allow_empty=False)
		else:
			choice = input(msg)
		return int(choice)

# --- Loaders ---
	def _load_ms_excel_spreadsheet(
			self,
			path: Path,
			*,
			sheet_name: Optional[str] = None,
			header: Optional[int] = None,
			dtype: Optional[dict] = None,
			include_hidden_rows: bool = False,
			**_: Any
	) -> pd.DataFrame:
		"""
		Load an Excel sheet into a DataFrame.

		- If ``sheet_name='choice'``, interactively list sheets and let the user pick.
		- If ``include_hidden_rows=True``, hidden rows are skipped via :mod:`openpyxl`.

		:param path: Excel file path.
		:param sheet_name: Sheet name or ``'choice'`` for interactive selection.
		:param header: Header row index (0-based).
		:param dtype: Optional dtype mapping for pandas.
		:param include_hidden_rows: Include hidden rows when True.
		:return: pandas.DataFrame
		"""
		load_workbook = openpyxl.load_workbook

		if sheet_name == "choice":
			wb = load_workbook(path, read_only=True, data_only=True)
			sheets = list(wb.sheetnames)
			wb.close()
			if not sheets:
				raise ValueError(f"No sheets in workbook: {path}")
			if len(sheets) > 1:
				choice = self._ask_choice_number("Available sheets:", sheets)
				sheet_name = sheets[choice - 1]
			else:
				sheet_name = sheets[0]
				LOG.info("Only one sheet found in the file: %s", sheet_name)

		if not include_hidden_rows:
			# filtered via openpyxl and DataFrame built 'by hand' (fast for small/middle lists).
			wb = load_workbook(path, data_only=True)
			ws = wb[sheet_name] if (sheet_name and sheet_name in wb.sheetnames) else wb.active
			rows: list[list[Any]] = []
			for row in ws.iter_rows():
				ridx = row[0].row
				if ws.row_dimensions[ridx].hidden:
					continue
				rows.append([cell.value for cell in row])
			wb.close()
			if not rows:
				return pd.DataFrame()
			# header considered if that makes sense
			if header is not None and 0 <= header < len(rows):
				cols = rows[header]
				data = rows[header + 1:]
				return pd.DataFrame(data, columns=cols, dtype=None if dtype is None else dtype)
			return pd.DataFrame(rows, dtype=None if dtype is None else dtype)

		return pd.read_excel(path, sheet_name=sheet_name, header=header, dtype=dtype)

	def _load_csv(
			self,
			path: Path,
			*,
			encoding: Optional[str] = None,
			delimiter: Optional[str] = None,
			header: Optional[int] = None,
			dtype: Optional[dict] = None,
			**_: Any
	) -> pd.DataFrame:
		"""
		Load CSV/TSV to DataFrame with best-effort encoding and delimiter detection.

		:param path: CSV-like file.
		:param encoding: Optional override (else autodetect).
		:param delimiter: Optional override (else autodetect).
		:param header: Header row index (0-based).
		:param dtype: Optional dtype mapping.
		:return: pandas.DataFrame
		"""
		enc = encoding or self.detect_encoding(path)
		delim = self._normalize_delim(delimiter) or self.detect_delimiter(path, encoding=enc)
		return pd.read_csv(path, encoding=enc, delimiter=delim, header=header, dtype=dtype)

	def _load_text_only(
			self,
			path: Path,
			*,
			encoding: Optional[str] = None,
			delimiter: Optional[str] = None,
			header: Optional[int] = None,
			dtype: Optional[dict] = None,
			**_: Any
	) -> pd.DataFrame:
		"""
		Load delimited text (.txt/.log) to DataFrame, similarly to CSV.

		:param path: Text file.
		:param encoding: Optional override (else autodetect).
		:param delimiter: Optional override (else autodetect).
		:param header: Header row index (0-based).
		:param dtype: Optional dtype mapping.
		:return: pandas.DataFrame
		"""
		enc = encoding or self.detect_encoding(path)
		delim = self._normalize_delim(delimiter) or self.detect_delimiter(path, encoding=enc)
		return pd.read_table(path, encoding=enc, delimiter=delim, header=header, dtype=dtype)

	@staticmethod
	def _load_json(path: Path, **_: Any) -> Iterable[dict | list]:
		"""
		Load JSON into native Python objects (dict/list).

		:param path: JSON file.
		:return: dict | list
		"""
		with open(path, "r", encoding="utf-8") as fh:
			return json.load(fh)

	@staticmethod
	def _load_xml(path: Path, **_: Any) -> pd.DataFrame:
		"""
		Parse simple XML into a flat DataFrame (child tags as columns).

		Note
		----
		This is a *very* simple flattener: it assumes a list-like XML with
		children that have only scalar child-tags.

		:param path: XML file.
		:return: pandas.DataFrame
		"""
		tree = ET.parse(path)
		root = tree.getroot()
		rows = [{child.tag: child.text for child in elem} for elem in root]
		return pd.DataFrame(rows)

	@staticmethod
	def _load_sif(fpath: Path, value_name: str = "value") -> pd.DataFrame:
		"""
		Load Andor SIF into a DataFrame via xarray-backed reader.

		Requires an external reader providing ``xr_open(path) -> xarray.DataArray``.

		:param fpath: SIF path.
		:param value_name: Column name for data values.
		:return: pandas.DataFrame
		:raises ImportError: when SIF reader is not available.
		"""

		da = sif.xr_open(str(fpath))
		df = da.to_dataframe(name=value_name).reset_index()
		# keep metadata
		try:
			df.attrs = dict(da.attrs)
		except Exception:
			pass
		return df
