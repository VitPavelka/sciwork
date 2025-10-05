from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


def get_logger(name: str = "sciwork") -> logging.Logger:
	"""
	Return a shared package logger (creates a console handler once).

	:param name: Logger name.
	:return: The configured logger.
	"""
	log = logging.getLogger(name)
	if not log.handlers:
		h = logging.StreamHandler()
		h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		log.addHandler(h)
	log.setLevel(logging.INFO)
	return log


def configure_logging(
		*,
		name: str = "sciwork",
		console_level: int = logging.INFO,
		file_path: Optional[PathLike] = None,
		file_level: Optional[int] = None,
		mode: str = "w",
		rotate: bool = False,
		max_bytes: int = 2_000_000,
		backup_count: int = 3,
		formatter: Optional[logging.Formatter] = None,
		propagate: bool = False
) -> logging.Logger:
	"""
	Configure a shared logger usable across SciWork packages.

	:param name: Logger name.
	:param console_level: Console handler level.
	:param file_path: Optional log file path to add a file handler.
	:param file_level: File handler level (defaults to console_level if None).
	:param mode: 'w' for overwriting or 'a' for appending.
	:param rotate: Use RotatingFileHandler when True.
	:param max_bytes: Rotation threshold per file.
	:param backup_count: Number of rotated backups.
	:param formatter: Custom formatter; default includes timestamp.
	:param propagate: Whether to propagate to parent loggers.
	:return: The configured logger.
	"""
	log = get_logger(name)
	log.setLevel(min(console_level, file_level or console_level))
	log.propagate = propagate

	fmt = formatter or logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

	has_stream = False
	for h in log.handlers:
		if isinstance(h, logging.StreamHandler):
			h.setLevel(console_level)
			h.setFormatter(fmt)
			has_stream = True
	if not has_stream:
		sh = logging.StreamHandler()
		sh.setLevel(console_level)
		sh.setFormatter(fmt)
		log.addHandler(sh)

	if file_path:
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		fh = (
			RotatingFileHandler(path, mode=mode, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
			if rotate else
			logging.FileHandler(path, mode=mode, encoding="utf-8")
		)
		fh.setLevel(file_level or console_level)
		fh.setFormatter(fmt)
		if not any(getattr(h, "baseFilename", None) == str(path) for h in log.handlers):
			log.addHandler(fh)

	return log
