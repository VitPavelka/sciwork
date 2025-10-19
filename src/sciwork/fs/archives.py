# src/sciwork/fs/archives.py

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from ..logutil import get_logger
from .base import PathLike, PathOpsBase
from ..imports import zipfile, pyzipper, tarfile, RARFILE
from .archive_utils import (
	detect_archive_type,
	safe_extract_zip, safe_extract_tar, safe_extract_rar,
	iter_archive_files,
	make_zip_archive, make_tar_archive
)

LOG = get_logger(__name__)

__all__ = ["Archives"]

ARCHIVE_SUFFIXES = {
		"zip": ".zip",
		"tar": ".tar",
		"gztar": ".tar.gz",
		"bztar": ".tar.bz2",
		"xztar": ".tar.xz",
		"rar": ".rar",
	}


class Archives(PathOpsBase):
	"""
	Archive utilities: safe extraction and creation of archives.

	- Heavy modules are imported lazily in helpers (zipfile, pyzipper, tarfile, rarfile).
	- Safe extraction with traversal protection via :func:`assert_within_dir`.
	- Respects :attr:`dry_run`.
	"""
	# --- Extract ---
	def _destination_dir(
			self, src: Path, extract_to: Optional[PathLike], *, overwrite: bool
	) -> Path:
		"""Figure out (and prepare) the output directory for extraction."""
		dest = self._abs(extract_to) if extract_to else src.with_suffix("")
		if dest.exists():
			# use Dirs.is_folder_empty for consistency
			try:
				try:
					from .dirs import Dirs
				except Exception:
					LOG.error("extract_archive requires the optional dependency 'sciwork.fs.Dirs' to work.")
					raise
				empty = Dirs().is_folder_empty(dest)
			except Exception:
				empty = False
			if not empty and not overwrite:
				raise FileExistsError(f"Destination not empty: '{dest}' (use overwrite=True).")
		else:
			if not self.dry_run:
				if dest.suffix == ".tar":
					dest = dest.with_suffix("")
				dest.mkdir(parents=True, exist_ok=True)
		return dest

	@staticmethod
	def _extract_zip(src: Path, dest: Path, *, password: Optional[str], safe: bool) -> None:
		"""
		Extract ZIP from *src* to *dest*. If *password* is provided, use pyzipper
		(AES/ZipCrypto); otherwise use the standard zipfile. Safe extraction (anti-traversal)
		via ``safe_extract_zip()``.
		"""
		if password:
			with pyzipper.AESZipFile(src, "r") as zf:
				if safe:
					safe_extract_zip(zf, dest, password=password)
				else:
					zf.setpassword(password.encode("utf-8"))
					zf.extractall(dest)
			return

		with zipfile.ZipFile(src, "r") as zf:
			if safe:
				safe_extract_zip(zf, dest, password=password)
			else:
				zf.extractall(dest)

	@staticmethod
	def _extract_tar(src: Path, dest: Path, *, safe: bool) -> None:
		"""Extract TAR archive."""
		with tarfile.open(src, "r:*") as tf:
			if safe:
				safe_extract_tar(tf, dest)
			else:
				tf.extractall(dest)

	@staticmethod
	def _extract_rar(src: Path, dest: Path, *, password: Optional[str], safe: bool) -> None:
		"""Extract RAR archive."""
		with RARFILE.RarFile(str(src), "r") as rf:  # type: ignore[attr-defined]
			if safe:
				safe_extract_rar(rf, dest, password=password)
			else:
				rf.extractall(path=str(dest), pwd=password)

	# --- Compress Helpers ---
	@staticmethod
	def _default_ext_for(format_name: Literal["zip", "tar", "gztar", "bztar", "xztar"]) -> str:
		"""Return the default extension for a given format name."""
		return ARCHIVE_SUFFIXES.get(format_name)

	def _ensure_archive_suffix(self, path: Path, arch_format: Literal["zip", "tar", "gztar", "bztar", "xztar"]) -> Path:
		"""Ensure the archive path has the correct suffix."""
		want = self._default_ext_for(arch_format)
		s = str(path)
		if s.lower().endswith(tuple(ARCHIVE_SUFFIXES.values())):
			return path
		return Path(s + want)

	def _resolve_output_path(
			self,
			src_dir: Path,
			output_archive_path: Optional[PathLike],
			arch_format: Literal["zip", "tar", "gztar", "bztar", "xztar"],
			*,
			overwrite: bool
	) -> Path:
		if output_archive_path is None:
			dest = src_dir.parent / (src_dir.name + self._default_ext_for(arch_format))
		else:
			dest = self._ensure_archive_suffix(self._abs(output_archive_path), arch_format)
			if not self.dry_run:
				dest.parent.mkdir(parents=True, exist_ok=True)

		if dest.exists() and not overwrite:
			raise FileExistsError(f"Archive already exists: '{dest}'.")

		return dest

	def _unlink_before_compression(self, dest: Path, overwrite: bool) -> None:
		"""Unlink the destination if it exists and ``overwrite=True``."""
		if dest.exists() and overwrite and not self.dry_run:
			try:
				dest.unlink()
			except FileNotFoundError:
				pass

	# --- Public API ---
	def extract_archive(
			self,
			archive_path: PathLike,
			extract_to: Optional[PathLike] = None,
			*,
			overwrite: bool = False,
			password: Optional[str] = None,
			safe: bool = True
	) -> Path:
		"""
		Extract an archive into a directory.

		Supported:
			- ZIP (password optional; legacy ZipCrypto)
			- TAR / TAR.GZ / TAR.BZ2 / TAR.XZ (no password)
			- RAR (password optional, requires mod:`rarfile` and an external backend)

		:param archive_path: Path to the archive file.
		:param extract_to: Target directory; default is ``<archive_dir>/<archive_stem>``.
		:param overwrite: Allow extraction into a non-empty target dir.
		:param password: Optional password for ZIP/RAR. Ignored for TAR*.
		:param safe: If True, protect against path traversal (recommended).
		:return: Absolute path to the extraction directory.
		:raises FileNotFoundError: Archive not found.
		:raises FileExistsError: Destination exists and is not empty and ``overwrite=False``.
		:raises ValueError: Unsupported type or password provided for unsupported format.
		:raises PermissionError: On OS errors.
		:raises OSError: On OS errors.
		"""
		src = self._abs(archive_path)
		if not src.exists():
			raise FileNotFoundError(f"Archive path does not exist: '{src}'.")

		dest = self._destination_dir(src, extract_to, overwrite=overwrite)

		kind = detect_archive_type(src)
		if kind == "unknown":
			raise ValueError(f"Unsupported or unrecognized archive type: '{src}'.")

		if self.dry_run:
			LOG.info("[dry-run] extract (%s): %s -> %s", kind, src, dest)
			return dest.resolve()

		try:
			if kind == "zip":
				self._extract_zip(src, dest, password=password, safe=safe)
			elif kind == "tar":
				if password:
					raise ValueError("Passwords are not supported for TAR archives.")
				self._extract_tar(src, dest, safe=safe)
			elif kind == "rar":
				self._extract_rar(src, dest, password=password, safe=safe)
			else:
				raise ValueError(f"Unsupported archive type: '{kind}'.")
		except PermissionError:
			LOG.exception("Permission denied while extracting '%s' -> '%s'", src, dest)
			raise
		except OSError as exc:
			LOG.exception("OS error while extracting '%s' -> '%s': %s", src, dest, exc)
			raise

		LOG.info("Extracted (%s): %s -> %s", kind, src, dest)
		return dest.resolve()

	def compress_to_archive(
			self,
			source: PathLike,
			output_archive_path: Optional[PathLike] = None,
			*,
			arch_format: Literal['zip', 'tar', 'gztar', 'bztar', 'xztar'] = "zip",
			overwrite: bool = False,
			password: Optional[str] = None,  # only for ZIP
			include_hidden: bool = True,
			compresslevel: Optional[int] = None  # 0..9 for zip / bz2
	) -> Path:
		"""
		Compress a directory into an archive (ZIP/TAR*). Supports password only for ZIP via pyzipper.

		:param source: Directory to compress.
		:param output_archive_path: Output archive path. If None, create alongside *source*
									with the appropriate extension.
		:param arch_format: 'zip' | 'tar' | 'gztar' | 'bztar' | 'xztar'
		:param overwrite: If True and output exist, remove it first.
		:param password: Optional password (ZIP only; AES-256 via pyzipper).
		:param include_hidden: Include dot-files/directories.
		:param compresslevel: Compression level (None for default).
		:return: Absolute path to the created archive.
		:raises FileNotFoundError: Source not found.
		:raises NotADirectoryError: Source is not a directory.
		:raises FileExistsError: Output exists and ``overwrite=False``.
		:raises ValueError: Invalid format or password used with TAR.
		"""
		src_dir = self._abs(source)
		if not src_dir.exists():
			raise FileNotFoundError(f"Source directory not found: '{src_dir}'.")
		if not src_dir.is_dir():
			raise NotADirectoryError(f"Source is not a directory: '{src_dir}'.")

		dest = self._resolve_output_path(src_dir, output_archive_path, arch_format, overwrite=overwrite)

		# prepare the file list
		files = list(iter_archive_files(src_dir, include_hidden=include_hidden))
		if not files:
			raise FileNotFoundError(f"No files to archive under '{src_dir}'.")

		if self.dry_run:
			LOG.info("[dry-run] make %s archive (%d files): %s -> %s", arch_format, len(files), src_dir, dest)
			return dest.resolve()

		if arch_format == "zip":
			self._unlink_before_compression(dest, overwrite=overwrite)
			make_zip_archive(src_dir, files, dest, password=password, compresslevel=compresslevel)
		else:
			if password:
				raise ValueError("Passwords are supported only for ZIP archives.")
			self._unlink_before_compression(dest, overwrite=overwrite)
			make_tar_archive(src_dir, files, dest, tar_format=arch_format, compresslevel=compresslevel)

		LOG.info("Archive created (%s): %s -> %s", arch_format, src_dir, dest)
		return dest.resolve()
