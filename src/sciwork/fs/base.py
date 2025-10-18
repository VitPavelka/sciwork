# src/sciwork/fs/base.py

from __future__ import annotations

from pathlib import Path
from typing import Callable, Union, Optional, Protocol

from ..logutil import get_logger

LOG = get_logger(__name__)

__all__ = ["PathLike", "PrompterProtocol", "PathOpsBase"]

PathLike = Union[str, Path]


class PrompterProtocol(Protocol):
	"""Callable that returns a user-entered string given a message."""
	def __call__(self, message: str) -> Union[str, bool]: ...


class PathOpsBase:
	"""
	Shared state and core helpers for filesystem operations.

	This base keeps a *root* directory for resolving relative paths, a global
	*dry-run* flag (log actions instead of touching the disk), and an injectable
	*input* function useful for confirmations and tests. Higher-level modules
	(delete, listdir, transfer, archives, ...) can subclass or accept an instance
	of this base to reuse the same context.

	:param base_dir: Base directory used to resolve relative paths. Defaults to ``Path.cwd()``.
	:param dry_run: When True, operations that would modify the filesystem only log
					the intended action and return early.
	:param input_func: Function used for interactive prompts. Defaults to :func:`input`.
	"""
	def __init__(
			self,
			base_dir: Optional[PathLike] = None,
			*,
			dry_run: bool = False,
			input_func: Optional[Callable[[str], str]] = None,
			**kwargs
	) -> None:
		self.base_dir = Path(base_dir).resolve() if base_dir else Path.cwd()
		self.dry_run = bool(dry_run)
		self.input_func = input_func or input

	# --- Construction helpers ---
	@classmethod
	def from_cwd(
			cls,
			*,
			dry_run: bool = False,
			input_func: Optional[Callable[[str], str]] = input,
			**kwargs
	) -> "PathOpsBase":
		"""
		Create an instance rooted at the current working directory.

		:param dry_run: If True, do not modify the filesystem (log-only).
		:param input_func: Function used for interactive confirmations.
		:return: PathOpsBase: A new instance with base_dir = Path.cwd().
		"""
		return cls(base_dir=Path.cwd(), dry_run=dry_run, input_func=input_func, **kwargs)

	@classmethod
	def at(
			cls,
			base: PathLike,
			*,
			dry_run: bool = False,
			input_func: Optional[Callable[[str], str]] = input,
			**kwargs
	) -> "PathOpsBase":
		"""
		Create an instance rooted at a given base directory.

		:param base: Base directory to anchor relative paths.
		:param dry_run: If True, do not modify the filesystem (log-only).
		:param input_func: Function used for interactive confirmations.
		:return: PathOpsBase: A new instance with base_dir = Path.cwd().
		"""
		return cls(base_dir=Path(base), dry_run=dry_run, input_func=input_func, **kwargs)

	# --- Path utilities ---
	def _abs(self, p: PathLike) -> Path:
		"""
		Resolve *p* relative to :attr:`base_dir` if it's not absolute.

		:param p: Absolute or relative file system path.
		:return: Absolute path.
		"""
		pth = Path(p)
		return pth if pth.is_absolute() else (self.base_dir / pth)

	@staticmethod
	def _apply_mode(target: Path, mode: Optional[int]) -> None:
		"""Best-effort chmod; log, do not propagate errors."""
		if mode is None:
			return
		try:
			target.chmod(mode)
		except Exception as exc:
			LOG.warning("Failed to chmod %o on %s: %s", mode, target, exc)

	def _pick_prompt(self, override: Optional[PrompterProtocol] = None, confirm=False) -> PrompterProtocol:
		"""
		Choose a (str)→str prompter.
			1) explicit override
			2) lazy import ``sciwork.console.Prompter().prompt``
			3) ``self.input_func`` (if present)
			4) builtin ``input``
		"""
		if override is not None:
			return override

		try:
			from ..console.prompter import Prompter
			if confirm:
				return Prompter().confirm
			return Prompter().prompt
		except Exception:
			pass

		f = getattr(self, "input_func", None)
		if callable(f):
			return f  # type: ignore[return-value]

		return input

	# --- Public API ---
	def coerce_file_path(self, path: PathLike) -> Path:
		"""
		Return an absolute path to a *file*.
		Rejects trailing path separators that make the path look like a directory.
		"""
		p = self._abs(path)
		raw = str(path)
		if raw.endswith(("/", "\\")):
			raise IsADirectoryError(f"Path looks like a directory (trailing slash): {raw!r}")
		return p

	def coerce_folder_path(self, path: PathLike) -> Path:
		"""Return an absolute path to a *folder*."""
		p = self._abs(path)
		if not p.is_dir():
			raise NotADirectoryError(f"Path is not a directory: {p!r}")
		return p

	# --- Dunder helpers ---
	def __str__(self) -> str:
		return f"{self.__class__.__name__}[base={self.base_dir}, dry_run={self.dry_run}]"

	def __repr__(self) -> str:
		return (
			f"{self.__class__.__name__}("
			f"base_dir={str(self.base_dir)!r}, dry_run={self.dry_run!r}, "
			f"input_func={getattr(self.input_func, '__name__', type(self.input_func).__name__)!r})"
		)
