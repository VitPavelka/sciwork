# src/sciwork/fs/encoding.py

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Optional

from ..logutil import get_logger
from .base import PathLike
from ..imports import MAGIC, charset_normalizer, chardet, pandas as pd

LOG = get_logger(__name__)

try:
	from .paths import Paths
except ImportError:
	LOG.error("Encoding class requires the optional dependency 'sciwork.fs.Paths' to work.")
	raise

__all__ = ["Encoding"]


class Encoding:
	"""
	Text encoding and delimiter utilities (best-effort, lazy optional deps).

	Pipeline for encoding detection (in order):
		1) libmagic: ``charset=...`` from MIME string
		2) charset-normalizer
		3) chardet
		4) small heuristic: try a few encodings with pandas quick-read

	Delimiter detection:
		- csv.Sniffer (sample)
		- pandas (probe candidates; pick first yielding >1 column)
	"""
	# --- Encoding detection ---
	@staticmethod
	def _detect_encoding_magic(sample: bytes) -> Optional[str]:
		"""
		Try libmagic on a byte sample: returns charset if present.

		:param sample: Initial byte sample from the file.
		:return: Encoding name if detected, else None.
		"""
		try:
			# python-magic compatible API
			m = MAGIC.Magic(mime=True)
			s = m.from_buffer(sample)  # e.g., "text/plain; charset=us-ascii"
			if s and "charset=" in s:
				enc = s.split("charset=", 1)[-1].strip()
				if enc:
					LOG.debug("Encoding '%s' detected by MAGIC.Magic", enc, s)
				return enc or None
		except Exception:
			return None
		return None

	@staticmethod
	def _detect_encoding_charset_normalizer(sample: bytes) -> Optional[str]:
		"""
		Try charset-normalizer on a byte sample.

		:param sample: Initial byte sample from the file.
		:return: Encoding name if detected, else None.
		"""
		try:
			res = charset_normalizer.from_bytes(sample)
			if res:
				best = res.best()
				if best and best.encoding:
					LOG.debug("Encoding '%s' detected by charset-normalizer", best.encoding)
					return best.encoding
		except Exception:
			pass
		return None

	@staticmethod
	def _detect_encoding_chardet(sample: bytes) -> Optional[str]:
		"""
		Try chardet on a byte sample.

		:param sample: Initial byte sample from the file.
		:return: Encoding name if detected, else None.
		"""
		try:
			guess = chardet.detect(sample)
			enc = guess.get("encoding")
			if enc:
				LOG.debug("Encoding '%s' detected by chardet", enc)
			return enc if enc else None
		except Exception:
			return None

	@staticmethod
	def _detect_encoding_heuristic(file_path: Path, prefer: Iterable[str]) -> Optional[str]:
		"""
		Heuristic attempt: try reading a few rows with pandas using preferred encodings.

		:param file_path: Path of the text file.
		:param prefer: Iterable of encodings to test (in order).
		:return: First encoding that works for a tiny read, else None.
		"""
		for enc in prefer:
			try:
				pd.read_table(file_path, encoding=enc, nrows=5)
				LOG.debug("Encoding '%s' detected by heuristic", enc)
				return enc
			except Exception:
				continue
		return None

	# --- Delimiter detection ---
	@staticmethod
	def _normalize_candidates(candidates: Iterable[str]) -> list[str]:
		"""
		Normalize candidate delimiter tokens (convert literal ``"\\t"`` to tab).
		"""
		out: list[str] = []
		for c in candidates:
			out.append("\t" if c == "\\t" else c)
		# make unique but keep order
		seen = set()
		uniq: list[str] = []
		for c in out:
			if c not in seen:
				seen.add(c)
				uniq.append(c)
		return uniq

	def _sniff_delimiter_sample(
			self,
			file_path: Path,
			*,
			encoding: str,
			candidates: Iterable[str],
			max_lines: int,
	) -> Optional[str]:
		"""
		Use :mod:`csv.Sniffer` to guess a delimiter from a short text sample.

		:param file_path: Text file path.
		:param encoding: Encoding to open the file.
		:param candidates: Iterable of candidate delimiter characters.
		:param max_lines: Max lines to read for the sample.
		:return: Detected delimiter or None.
		"""
		cand = self._normalize_candidates(candidates)

		sample_lines: list[str] = []
		try:
			with open(file_path, "r", encoding=encoding, errors="replace") as fh:
				for _ in range(max_lines):
					line = fh.readline()
					if not line:
						break
					sample_lines.append(line)
			if not sample_lines:
				return None
			sample = "".join(sample_lines)
			dialect = csv.Sniffer().sniff(sample, delimiters="".join(cand))
			delim = getattr(dialect, "delimiter", None)
			if delim and delim in set(cand):
				LOG.debug("Delimiter '%s' detected by csv.Sniffer", delim)
				return delim  # type: ignore[return-value]
		except Exception:
			return None
		return None

	def _pandas_guess_delimiter(
			self,
			file_path: Path,
			*,
			encoding: str,
			candidates: Iterable[str],
	) -> Optional[str]:
		"""
		Try candidate delimiters with pandas and pick the first yielding >1 column.

		:param file_path: Text file path.
		:param encoding: Encoding to open the file.
		:param candidates: Iterable of candidate delimiter characters.
		:return: Detected delimiter or None.
		"""
		for delim in self._normalize_candidates(candidates):
			try:
				df = pd.read_csv(file_path, encoding=encoding, delimiter=delim, nrows=10)
				if getattr(df, "shape", (1, 1))[1] > 1:
					LOG.debug("Delimiter '%s' detected by pandas", delim)
					return delim
			except Exception:
				continue
		return None

	# --- Main Methods ---
	def detect_encoding(
			self,
			file_path: PathLike,
			*,
			sample_size: int = 4096,
			prefer: Optional[list[str]] = None
	) -> str:
		"""
		Detect text encoding of a file (best-effort; optimized for Central European texts).

		Detection pipeline:
			1) :meth:`_detect_encoding_magic`
			2) :meth:`_detect_encoding_charset_normalizer`
			3) :meth:`_detect_encoding_chardet`
			4) :meth:`_detect_encoding_heuristic`

		:param file_path: Path to the file.
		:param sample_size: Bytes to sample for heuristics.
		:param prefer: Optional list of encodings to try first (e.g., ["utf-8-sig","cp1250"]).
		:return: Encoding name (e.g., "utf-8").
		:raises FileNotFoundError: If the file doesn't exist.
		:raises OSError: On IO errors.
		"""
		p = Paths().coerce_file_path(file_path)
		if not p.exists():
			raise FileNotFoundError(f"File not found: '{file_path}'.")

		prefer = prefer or ["utf-8", "utf-8-sig", "cp1250", "windows-1250", "cp1252", "iso-8859-2", "latin-1"]

		with open(p, "rb") as fh:
			sample = fh.read(sample_size)

		enc = (
				self._detect_encoding_magic(sample)
				or self._detect_encoding_charset_normalizer(sample)
				or self._detect_encoding_chardet(sample)
				or self._detect_encoding_heuristic(p, prefer)
		)

		if enc:
			return enc

		LOG.warning("Encoding detection unsuccessful. "
		            "Falling back to 'utf-8' encoding for %s", p)
		return "utf-8"

	def detect_delimiter(
			self,
			file_path: PathLike,
			*,
			encoding: Optional[str] = None,
			candidates: Optional[list[str]] = None,
			max_lines: int = 50,
			single_column_placeholder: str = "~"
	) -> str:
		"""
		Detect a reasonable delimiter for a delimited text file.

		Pipeline:
			1) :meth:`_sniff_delimiter_sample` (csv.Sniffer)
			2) :meth:`_pandas_guess_delimiter` (quick DataFrame probes)

		:param file_path: Text file path.
		:param encoding: Text encoding; if None, runs :meth:`detect_encoding` first.
		:param candidates: Candidate delimiters to try, default [',',';','\\t','|',':'].
		:param max_lines: Number of lines to sample for sniffer.
		:param single_column_placeholder: Return value when only one column is detected.
		:return: Detected delimiter string.
		:raises FileNotFoundError: If the file doesn't exist.
		"""
		p = Paths().coerce_file_path(file_path)
		if not p.exists():
			raise FileNotFoundError(f"File not found: '{file_path}'.")

		if encoding is None:
			encoding = self.detect_encoding(p)

		candidates = candidates or [",", ";", "\\t", "|", ":"]

		delim = (
				self._sniff_delimiter_sample(p, encoding=encoding, candidates=candidates, max_lines=max_lines)
				or self._pandas_guess_delimiter(p, encoding=encoding, candidates=candidates)
		)
		if delim:
			return delim

		LOG.warning("No valid delimiter found for %s. Assuming single-column.", p)
		return single_column_placeholder
