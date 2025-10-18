# src/sciwork/fs/archive_utils.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Literal, Optional, Any

from ..logutil import get_logger
from .inspect import build_metadata
from ..imports import zipfile, tarfile, pyzipper

LOG = get_logger(__name__)

__all__ = [
	"detect_archive_type",
	"assert_within_dir",
	"safe_extract_zip", "safe_extract_tar", "safe_extract_rar",
	"iter_archive_files",
	"make_zip_archive", "make_tar_archive"
]


# --- Detection & safety ---
def detect_archive_type(archive: Path) -> Literal["zip", "tar", "rar", "unknown"]:
	"""
	Best-effort archive kind detection: 'zip' | 'tar' | 'rar' | 'unknown'.

	:param archive: Path to the archive file.
	:return: Type of the archive.
	"""
	p = Path(archive)
	name = p.name.lower()

	# 1) Fast guess based on file extension
	if name.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
		return "tar"
	if name.endswith(".zip"):
		return "zip"
	if name.endswith(".rar"):
		return "rar"

	# 2) MIME hint from build_metadata()
	meta = build_metadata(p) or {}
	mime = (meta.get("mime") or "").lower()
	if mime in {"application/zip", "application/x-zip-compressed"}:
		return "zip"
	if mime in {"application/x-tar", "application/x-gtar"}:
		return "tar"
	if mime in {"application/vnd.rar", "application/x-rar-compressed"}:
		return "rar"

	# Light "magic" sniff without external dependencies
	try:
		with open(p, "rb") as f:
			head = f.read(8)

			# ZIP (local/EOCD/spanned)
			if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06") or head.startswith(b"PK\x07\x08"):
				return "zip"

			# RAR 4.x and 5.x
			if head.startswith(b"Rar!\x1a\x07\x00") or head.startswith(b"Rar!\x1a\x07\x01\x00"):
				return "rar"

			# TAR: 'ustar' signature at offset 257
			f.seek(257)
			sig = f.read(6)
			if sig.startswith(b"ustar"):
				return "tar"
	except Exception:
		pass

	return "unknown"


def assert_within_dir(base_dir: Path, target: Path) -> None:
	"""
	Ensure *target* remains within *base_dir* (prevents path traversal on extract).

	:raises ValueError: If *target* escapes *base_dir*.
	"""
	base_dir = base_dir.resolve()
	target = Path(target).resolve()
	if base_dir not in target.parents and base_dir != target:
		raise ValueError(f"Blocked path traversal: {target} not within {base_dir}.")


# --- Safe Extraction Helpers ---
def safe_extract_zip(zf: Any, dest: Path, *, password: Optional[str]) -> None:
	"""
	Extract ZIP entries to *dest* with traversal protection.

	:param zf: Instance of :class:`zipfile.ZipFile`.
	:param dest: Destination directory.
	:param password: Password to use, if any.
	"""
	pwd = password.encode("utf-8") if password else None
	if pwd and hasattr(zf, "setpassword"):
		zf.setpassword(pwd)
	for info in zf.infolist():
		name = info.filename
		# zip can contain both folders and files
		target = dest / Path(name)
		assert_within_dir(dest, target.parent if info.is_dir() else target)

		if info.is_dir():
			target.mkdir(parents=True, exist_ok=True)
			continue

		target.parent.mkdir(parents=True, exist_ok=True)
		with zf.open(name) as src, open(target, "wb") as out:
			out.write(src.read())


def safe_extract_tar(tf: Any, dest: Path) -> None:
	"""
	Extract TAR entries to *dest* with traversal protection.

	:param tf: Instance of :class:`tarfile.TarFile`.
	:param dest: Destination directory.
	"""
	for member in tf.getmembers():
		target = dest / Path(member.name)
		assert_within_dir(dest, target.parent if member.isdir() else target)
		tf.extract(member, dest)  # guarded by the check above


def safe_extract_rar(rf: Any, dest: Path, *, password: Optional[str]) -> None:
	"""
	Extract RAR entries to *dest* with traversal protection.

	:param rf: Instance of :class:`rarfile.RarFile`.
	:param dest: Destination directory.
	:param password: Password to use, if any.
	"""
	for info in rf.infolist():
		target = dest / Path(info.filename)
		# rarfile has info.isdir()
		assert_within_dir(dest, target.parent if getattr(info, "isdir", lambda: False)() else target)
	rf.extractall(path=str(dest), pwd=password)


# --- File Enumeration (for compression) ---
def iter_archive_files(src_dir: Path, *, include_hidden: bool = True) -> Iterable[Path]:
	"""
	Yield files under *src_dir* recursively. Optionally, skip dot-entries.
	"""
	root = Path(src_dir)
	for p in root.rglob("*"):
		if p.is_dir():
			continue
		if not include_hidden:
			try:
				rel = p.relative_to(root)
				if any(part.startswith(".") for part in rel.parts):
					continue
			except Exception:
				if p.name.startswith("."):
					continue
		yield p


# --- Compression Helpers ---
def make_zip_archive(
		src_dir: Path,
		files: Iterable[Path],
		dest_zip: Path,
		*,
		password: Optional[str],
		compresslevel: Optional[int],
) -> None:
	"""
	Create a ZIP archive at *dest_zip* from *files* under *src_dir*.

	If *password* is provided, use AES-256 via ``pyzipper`` (lazy import).
	"""

	comp = zipfile.ZIP_DEFLATED
	kwargs = {"compression": comp}
	if compresslevel is not None:
		kwargs["compresslevel"] = compresslevel

	if password:
		with pyzipper.AESZipFile(dest_zip, "w", **kwargs) as zf:
			zf.setpassword(password.encode("utf-8"))
			zf.setencryption(pyzipper.WZ_AES, nbits=256)
			for f in files:
				arcname = Path(f).relative_to(src_dir)
				zf.write(f, arcname)
		return

	# Plain ZIP (no password)
	with zipfile.ZipFile(dest_zip, "w", **kwargs) as zf:
		for f in files:
			arcname = Path(f).relative_to(src_dir)
			zf.write(f, arcname)


def make_tar_archive(
		src_dir: Path,
		files: Iterable[Path],
		dest_tar: Path,
		*,
		tar_format: Literal['tar', 'gztar', 'bztar', 'xztar'],
		compresslevel: Optional[int]
) -> None:
	"""
	Create a TAR-based archive at *dest_tar* from *files* under *src_dir*.

	:param src_dir: Source directory.
	:param files: Iterable of files to include.
	:param dest_tar: Destination archive file.
	:param tar_format: 'tar' | 'gztar' | 'bztar' | 'xztar'
	:param compresslevel: Compression level (None for default).
	"""
	mode_map = {
		"tar": "w",
		"gztar": "w:gz",
		"bztar": "w:bz2",
		"xztar": "w:xz"
	}
	mode = mode_map.get(tar_format)
	if mode is None:
		raise ValueError(f"Unsupported TAR format: '{tar_format}'.")

	# tarfile.open supports compresslevel for bz2; ignored for plain tar/gz/xz
	compress_invalid = {'tar', 'gztar', 'xztar'}
	if compresslevel is None or tar_format in compress_invalid:
		if tar_format in compress_invalid:
			LOG.warning(f"tarfile.open() does not support compression level for plain {tar_format} archives. "
			            f"Compresslevel not applied...")
		tf = tarfile.open(dest_tar, mode)
	else:
		tf = tarfile.open(dest_tar, mode, compresslevel=compresslevel)
	with tf:
		for f in files:
			arcname = Path(f).relative_to(src_dir)
			tf.add(f, arcname=str(arcname))
