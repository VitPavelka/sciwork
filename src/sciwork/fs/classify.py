# src/sciwork/fs/classify.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

from ..logutil import get_logger
from .inspect import build_metadata

LOG = get_logger(__name__)

try:
	from .paths import Paths
except ImportError:
	LOG.error("Classify class requires the optional dependency 'sciwork.fs.Paths' to work.")
	raise

__all__ = ["Classify"]


class Classify:
	"""
	Lightweight file/folder classifier.

	Classification is primarily based on the MIME type returned by
	:func:`~sciwork.fs.inspect.build_metadata` (the filename-based best effort).
	A small extension fallback table is applied if MIME is missing/unknown.

	Returned labels are simple strings as ``"folder"``, ``"image"``, ``"ms_excel_spreadsheet"``,
	``"comma_separated_values"``, ``"portable_document_format"``, etc. or ``"unknown"``.
	"""
	#: Minimal extension fallback when MIME is not usable.
	DEFAULT_TYPE_BY_EXT: Dict[str, str] = {
		".xlsx": "ms_excel_spreadsheet",
		".xlsm": "ms_excel_spreadsheet",
		".xls": "ms_excel_spreadsheet",
		".csv": "comma_separated_values",
		".tsv": "comma_separated_values",
		".txt": "text_only",
		".log": "text_only",
		".json": "javascript_object_notation",
		".xml": "extensible_markup_language",
		".pdf": "portable_document_format",
		".zip": "zip_archive",
		".tar": "tar_archive",
		".gz": "tar_archive",
		".bz2": "tar_archive",
		".xz": "tar_archive",
		".rar": "rar_archive",
		".sif": "andor_scientific_image_format",
		".spc": "uv_vis_spectrum_spc"
	}

	@staticmethod
	def _from_mime(mime: Optional[str]) -> Optional[str]:
		"""
		Map a MIME string to a coarse label. Return ``None`` if not recognized.
		"""
		if not mime:
			return None

		m = mime.lower()

		# broad families
		if m.startswith("image/"):
			return "image"
		if m.startswith("video/"):
			return "video"
		if m.startswith("audio/"):
			return "audio"
		if m.startswith("text/"):
			if m in {"text/csv", "text/tab-separated-values"}:
				return "comma_separated_values"
			if m == "text/xml":
				return "extensible_markup_language"
			return "text_only"

		# common apps
		if m in {
			"application/vnd.ms-excel",
			"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			"application/vnd.ms-excel.sheet.macroenabled.12"
		}:
			return "ms_excel_spreadsheet"

		if m == "application/pdf":
			return "portable_document_format"

		if m == "application/json":
			return "javascript_object_notation"

		# archive types
		if m in {"application/zip", "application/x-zip-compressed"}:
			return "zip_archive"
		if m in {"application/x-tar", "application/x-gtar"}:
			return "tar_archive"
		if m in {"application/vnd.rar", "application/x-rar-compressed"}:
			return "rar_archive"

		# data formats
		if m == "application/x-pkcs7-certificates":
			return "uv_vis_spectrum_spc"

		return None

	def classify_path(self, path: Union[Path, str]) -> str:
		"""
		Classify a path using MIME-first + extension fallback.

		:param path: Target path (absolute or relative to ``base_dir``).
		:return: ``"folder"`` | a known label | ``"unknown"``
		"""
		p = Paths().resolve_path(path)
		if p.is_dir():
			return "folder"

		meta = build_metadata(p)  # includes MIME via mimetypes on the filename
		label = self._from_mime(meta.get("mime"))
		if label:
			return label

		ext = p.suffix.lower()
		if ext in self.DEFAULT_TYPE_BY_EXT:
			return self.DEFAULT_TYPE_BY_EXT[ext]

		return "unknown"
