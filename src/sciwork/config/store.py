from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union, Literal

LOG = logging.getLogger(__name__)

PathLike = Union[str, Path]


# --- Directory resolution
def user_config_dir(app: str = "sciwork") -> Path:
	"""
	Return a per-user configuration directory.

	On Windows this is ``%APPDATA%/<app>``, on POSIX ``$XDG_CONFIG_HOME/<app>`` or ``~/.config/<app>``.

	:param app: Application namespace directory name.
	:return: Absolute path to the user config directory (not guaranteed to exist).
	"""
	if os.name == "nt":
		base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
	else:
		base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
	return (base / app).resolve()


def project_config_dir(project_root: Optional[PathLike] = None, app: str = "sciwork") -> Path:
	"""
	Return a project-local configuration directory ``<project_root>/<app>/configs``.

	:param project_root: Project root directory. If ``None``, uses ``Path.cwd()``.
	:param app: Application namespace directory name.
	:return: Absolute path to the project config directory (not guaranteed to exist).
	"""
	root = Path(project_root) if project_root is not None else Path.cwd()
	return (root / app / "configs").resolve()


def resolve_config_path(
		name: str,
		*,
		prefer: Literal['user', 'project'] = "user",
		project_root: Optional[PathLike] = None,
		env_var: Optional[str] = None,
		app: str = "sciwork",
) -> Path:
	"""
	Resolve an absolute path for a config file *name* with a clear precedence.

	Precedence:
		1) If ``env_var`` is provided and the environment variable is set → use that path.
		2) If ``prefer == 'project'`` → ``project_config_dir(project_root)/name``.
		3) Otherwise → ``user_config_dir(app)/name``.

	:param name: File name (e.g., ``"ansi_colors.json"``).
	:param prefer: Either ``'user'`` or ``'project'``.
	:param project_root: Optional project root for project-local resolution.
	:param env_var: Optional environment variable that can override the path.
	:param app: Application namespace directory.
	:return: The absolute path (may or may not exist yet).
	:raises ValueError: If ``prefer`` is not ``'user'`` or ``'project'``.
	"""
	if env_var:
		override_var = os.getenv(env_var)
		if override_var:
			return Path(override_var).expanduser().resolve()

	if prefer == 'project':
		return (project_config_dir(project_root, app) / name).resolve()
	if prefer == 'user':
		return (user_config_dir(app) / name).resolve()

	raise ValueError(f"prefer must be 'user' or 'project', not {prefer}")


# --- Low-level atomic I/O
def _ensure_parent(path: Path) -> None:
	"""Create parent directories for *path* if missing."""
	path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write_text(dest: Path, text: str, *, encoding: str = "utf-8", backup_ext: Optional[str] = None) -> None:
	"""
	Atomically write *text* to *dest*. Optionally, create a backup of the original.

	Strategy:
		- write to a temporary file in the same directory,
		- flush + fsync,
		- optional backup,
		- os.replace(temp, dest) (atomic on POSIX/NTFS).

	:param dest: Destination file path.
	:param text: Text content to write.
	:param encoding: Target encoding.
	:param backup_ext: If provided (e.g., ``".bak"``), make a backup of *dest* when it exists.
	:raises OSError: On I/O errors.
	"""
	_ensure_parent(dest)
	tmp_fd, tmp_path = tempfile.mkstemp(prefix=dest.name + ".", dir=str(dest.parent))
	try:
		with os.fdopen(tmp_fd, "w", encoding=encoding, newline="\n") as fh:
			fh.write(text)
			fh.flush()
			os.fsync(fh.fileno())

		if backup_ext and dest.exists():
			backup = dest.with_suffix(dest.suffix + backup_ext)
			try:
				if backup.exists():
					backup.unlink()
				dest.replace(backup)
			except Exception:
				LOG.warning("Failed to create backup for %s", dest, exc_info=True)

		os.replace(tmp_path, dest)
	except Exception:
		# best-effort cleanup
		try:
			if os.path.exists(tmp_path):
				os.remove(tmp_path)
		except Exception:
			pass
		raise


def _atomic_write_json(dest: Path, obj: Any, *, indent: int = 2, backup_ext: Optional[str] = None) -> None:
	"""
	Atomically write JSON *obj* to *dest* with UTF-8 encoding.

	:param dest: Destination file path.
	:param obj: JSON-serializable object to write.
	:param indent: Indentation for readability.
	:param backup_ext: Optional backup extension (e.g., ``".bak"``).
	:raises TypeError: If *obj* is not JSON serializable.
	:raises OSError: On I/O errors.
	"""
	text = json.dumps(obj, ensure_ascii=False, indent=indent)
	_atomic_write_text(dest, text, encoding="utf-8", backup_ext=backup_ext)


# --- Public API: read/write helpers
def ensure_config_file(path: PathLike, *, initial: Optional[str] = None, overwrite: bool = False) -> Path:
	"""
	Ensure a text config file exists at *path*. If missing (or ``overwrite=True``), write *initial*.

	:param path: Target config path.
	:param initial: Initial file content to write (empty string when None).
	:param overwrite: Rewrite even if the file already exists.
	:return: The absolute path to the file.
	:raises OSError: On I/O errors.
	"""
	dest = Path(path).expanduser().resolve()
	if dest.exists() and not overwrite:
		return dest
	_atomic_write_text(dest, initial or "", encoding="utf-8", backup_ext=None)
	LOG.info("Created config file at %s", dest)
	return dest


def read_text(path: PathLike, *, encoding: str = "utf-8") -> str:
	"""
	Read a text file.

	:param path: File path.
	:param encoding: Text encoding.
	:return: File contents as a string.
	:raises FileNotFoundError: If the file does not exist.
	:raises OSError: On I/O errors.
	"""
	p = Path(path).expanduser().resolve()
	with p.open("r", encoding=encoding) as fh:
		return fh.read()


def write_text(
		path: PathLike,
		text: str,
		*,
		encoding: str = "utf-8",
		overwrite: bool = True,
		backup_ext: Optional[str] = ".bak"
) -> Path:
	"""
	Write a text file atomically, optionally creating a backup of the previous content.

	:param path: Destination path.
	:param text: Content to write.
	:param encoding: Target encoding.
	:param overwrite: If ``False`` and the file exist, raise ``FileExistsError``.
	:param backup_ext: Backup extension; set ``None`` to disable backups.
	:return: Absolute path written.
	:raises FileExistsError: When destination exists and ``overwrite=False``.
	:raises OSError: On I/O errors.
	"""
	dest = Path(path).expanduser().resolve()
	if dest.exists() and not overwrite:
		raise FileExistsError(f"Destination file already exists at {dest}")
	_atomic_write_text(dest, text, encoding=encoding, backup_ext=backup_ext)
	LOG.info("Wrote text to %s", dest)
	return dest


def read_json(path: PathLike) -> Any:
	"""
	Read and parse JSON from *path*.

	:param path: JSON file path.
	:return: Parsed Python object.
	:raises FileNotFoundError: If the file does not exist.
	:raises json.JSONDecodeError: For invalid JSON.
	:raises OSError: On I/O errors.
	"""
	p = Path(path).expanduser().resolve()
	with p.open("r", encoding="utf-8") as fh:
		return json.load(fh)


def write_json(
		path: PathLike,
		obj: Any,
		*,
		indent: int = 2,
		overwrite: bool = True,
		backup_ext: Optional[str] = ".bak"
) -> Path:
	"""
	Write JSON atomically, optionally creating a backup.

	:param path: Destination JSON path.
	:param obj: JSON-serializable object to write.
	:param indent: Indent for pretty output.
	:param overwrite: If ``False`` and the file exist, raise ``FileExistsError``.
	:param backup_ext: Backup extension (``None`` disables backups).
	:return: The absolute path of the file.
	:raises FileExistsError: If destination exists and ``overwrite=False``.
	:raises TypeError: If the object is not JSON-serializable.
	:raises OSError: On I/O errors.
	"""
	dest = Path(path).expanduser().resolve()
	if dest.exists() and not overwrite:
		raise FileExistsError(f"Destination file already exists at {dest}")
	_atomic_write_json(dest, obj, indent=indent, backup_ext=backup_ext)
	LOG.info("Wrote JSON to %s", dest)
	return dest


def list_configs(directory: PathLike, pattern: str = "*.json") -> list[Path]:
	"""
	Return a list of config files in *directory* matching *pattern*.

	:param directory: Directory to search for config files.
	:param pattern: Glob pattern (default ``*.json``).
	:return: List of absolute Paths.
	"""
	d = Path(directory).expanduser().resolve()
	return sorted(p.resolve() for p in d.glob(pattern))


__all__ = [
	"PathLike",
	"user_config_dir",
	"project_config_dir",
	"resolve_config_path",
	"ensure_config_file",
	"read_text",
	"write_text",
	"read_json",
	"write_json",
	"list_configs"
]
