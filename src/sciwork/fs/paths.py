# src/sciwork/fs/paths.py
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, Optional, Literal

from ..logutil import get_logger
from .base import PathLike, PathOpsBase, PrompterProtocol

LOG = get_logger(__name__)

__all__ = ["Paths"]


class Paths(PathOpsBase):
	"""Small helper layer with user-facing path utilities."""
	# --- Helpers ---
	@staticmethod
	def _normalize_exts(exts: Optional[Iterable[str]]) -> set[str]:
		"""Normalize an extension list to lower-case with a leading dot."""
		if not exts:
			return set()
		out: set[str] = set()
		for e in exts:
			t = str(e).strip().lower()
			if not t:
				continue
			out.add(t if t.startswith(".") else f".{t}")
		return out

	@staticmethod
	def _default_prompt(*, kind: str, has_default: bool) -> str:
		"""Create a readable prompt message."""
		suffix = " (leave empty for default)" if has_default else ""
		if kind in {'file', 'folder'}:
			return f"Enter the path to the {kind}{suffix} (Ctrl+Shift+C to copy the {kind}path)"
		return f"Enter the path (Ctrl+Shift+C to copy the path)"

	@staticmethod
	def _looks_like_dir(raw: str) -> bool:
		"""Heuristic for directory-like input (trailing slash)."""
		return raw.endswith("/") or raw.endswith("\\")

	@staticmethod
	def _type_guard(path: Path, *, kind: str) -> None:
		"""Ensure the existing path matches the requested kind, else raise."""
		if kind == "file" and path.is_dir():
			raise IsADirectoryError(f"Path looks like a directory (trailing slash): {path!r}")
		if kind == "folder" and not path.is_dir():
			raise NotADirectoryError(f"Path is not a directory: {path!r}")

	# --- Public API ---
	def resolve_path(self, *parts: PathLike) -> Path:
		"""
		Join one or more path *parts* relative to ``base_dir`` (unless the first
		part is absolute) and return an absolute, resolved path.

		:param parts: Path segments (``str`` or :class:`pathlib.Path`). If empty, returns
						``base_dir.resolve()``.
		:return: Absolute, resolved path.
		"""
		if not parts:
			return self.base_dir.resolve()

		first = Path(parts[0])
		p = first if first.is_absolute() else (self.base_dir / first)
		for seg in parts[1:]:
			p = p / Path(seg)
		return p.resolve()

	def rename_path(
			self,
			old_path: PathLike,
			new_path: PathLike,
			*,
			overwrite: bool = False,
			create_parents: bool = True
	) -> Path:
		"""
		Rename (or move within the same filesystem) a path to a new path.

		If *new_path* is an existing directory, the entry will be moved **into** it
		under its original name.

		This prefers :py:meth:`Path.rename` (atomic on the same FS). If it fails
		with EXDEV (cross-device), it falls back to :func:`shutil.move`.

		:param old_path: Existing file or directory.
		:param new_path: The target file or directory path or existing directory.
		:param overwrite: If True, remove an existing target before renaming.
		:param create_parents: Ensure the parent directory for the target exists.
		:return: Absolute resolved target path.
		:raises FileNotFoundError: Old path does not exist.
		:raises FileExistsError: Target exists and the ``overwrite=False``.
		:raises PermissionError, OSError: On OS-level errors.
		"""
		try:
			from .transfer import Transfer
		except ImportError:
			LOG.error("'rename_path' method requires the optional dependency 'sciwork.fs.Transfer' to work.")
			raise

		src, target = Transfer().prepare_transfer(
			old_path, new_path,
			overwrite=overwrite, create_parents=create_parents
		)

		if self.dry_run:
			LOG.info("[dry-run] rename %s -> %s", src, target)
			return target.resolve()

		# Try atomic rename first; fallback to shutil.move on EXDEV
		try:
			src.rename(target)
		except OSError as exc:
			if getattr(exc, "errno", None) in (18, getattr(os, "EXDEV", 18)):
				try:
					shutil.move(str(src), str(target))
				except Exception:
					LOG.exception("shutil.move fallback failed: %s -> %s", src, target)
					raise
			else:
				LOG.exception("OS error while renaming '%s' -> '%s': %s", src, target, exc)
				raise

		LOG.info("Renamed %s -> %s", src, target)
		return target.resolve()

	def prompt_path(
			self,
			*,
			kind: Literal['file', 'folder', 'any'] = "any",
			must_exist: bool = True,
			allowed_exts: Optional[Iterable[str]] = None,
			default: Optional[PathLike] = None,
			prompt: Optional[str] = None,
			prompter: Optional[PrompterProtocol] = None
	) -> Optional[Path]:
		"""
		Prompt the user for a file or folder path and validate it.

		The prompter selection processes in this order:
		1) explicit ``prompter`` argument if provided,
		2) method ``self.prompt`` (from :class:`sciwork.console.Prompter`, if available),
		3) attribute ``self.input_func`` (if present),
		4) builtin :func:`input`.

		:param kind: Either ``"file"``, ``"folder"`` or ``"any"`` (default).
		:param must_exist: When ``True``, the path must exist and match the requested ``kind``.
		:param allowed_exts: Optional iterable of allowed file extensions (e.g., ``['.csv', '.jpg']``).
							 Only enforced when ``kind="file"``. Case-insensitive; dots are optional.
		:param default: Optional default value returned when the user submits an empty input.
		:param prompt: Optional custom prompt text. If ``None``, a sensible default is used.
		:param prompter: Optional callable to ask the user. If omitted, it tries to use
						 ``self.prompt`` / ``self.input_func`` / builtin ``input``.
		:return: Absolute, resolved path.
		:raises ValueError: If ``kind`` is invalid or file extension is not allowed.
		:raises NotADirectoryError: When ``kind="folder"`` but the path is not a directory (for existing paths).
		:raises IsADirectoryError: When ``kind="file"`` but the path is a directory.
		"""
		if kind not in {"file", "folder", "any"}:
			raise ValueError(f"kind must be 'file' or 'folder': {kind!r}")

		ask = self._pick_prompt(prompter)
		norm_exts = self._normalize_exts(allowed_exts)
		message = prompt or self._default_prompt(kind=kind, has_default=default is not None)

		while True:
			raw = ask(message).strip().strip('"').strip("'")
			if not raw and default is not None:
				raw = str(default)

			# expand env/home and resolve relative to base_dir
			s = os.path.expandvars(os.path.expanduser(raw))
			candidate = self._abs(s)

			# must-exist logic and type guard
			if must_exist:
				if not candidate.exists():
					# re-prompt when missing
					continue
				self._type_guard(candidate, kind=kind)
			else:
				if candidate.exists():
					self._type_guard(candidate, kind=kind)
				else:
					# for a would-be file, reject obvious directory-like input (trailing slash)
					if kind == "file" and self._looks_like_dir(raw):
						raise IsADirectoryError(f"Path looks like a directory (trailing slash): {raw!r}")

			# extension filter for files
			if kind == "file" and norm_exts:
				ext = candidate.suffix.lower()
				if ext not in norm_exts:
					raise ValueError(
						f"File must have one of the extensions: {sorted(norm_exts)} (got {ext or '<none>'})."
					)

			return candidate.resolve()
