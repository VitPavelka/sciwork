# src/sciwork/logutil.py

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal, Optional, Union

PathLike = Union[str, Path]

ConsoleLevelName = Literal[
	"CRITICAL",
	"FATAL",
	"ERROR",
	"WARNING",
	"WARN",
	"INFO",
	"DEBUG",
	"NOTSET",
]

LevelLike = Union[int, ConsoleLevelName]


def _normalize_level(value: LevelLike, *, param_name: str) -> int:
	if isinstance(value, int):
		return value

	resolved = logging.getLevelName(value.upper())
	if isinstance(resolved, int):
		return resolved

	raise ValueError(f"Unknown logging level name for {param_name}: {value}")

def get_logger(name: str = "sciwork") -> logging.Logger:
	"""
	Return a shared package logger (creates a console handler once).

	:param name: Logger name.
	:return: The configured logger.
	"""
	log = logging.getLogger(name)
	if not log.handlers:
		handler = logging.StreamHandler()
		handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		log.addHandler(handler)
	log.setLevel(logging.INFO)
	return log


def configure_logging(
		*,
		name: str = "sciwork",
		console_level: ConsoleLevelName = "INFO",
		file_path: Optional[PathLike] = None,
		file_level: Optional[LevelLike] = None,
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
	:param file_level: File handler level (int or level name,
					   defaults to console-level if None).
	:param mode: 'w' for overwriting or 'a' for appending.
	:param rotate: Use RotatingFileHandler when True.
	:param max_bytes: Rotation threshold per file.
	:param backup_count: Number of rotated backups.
	:param formatter: Custom formatter; default includes timestamp.
	:param propagate: Whether to propagate to parent loggers.
	:return: The configured logger.
	"""
	console_level_value = _normalize_level(console_level, param_name="console_level")
	file_level_value = (
		_normalize_level(file_level, param_name="file_level")
		if file_level is not None
		else None
	)

	log = get_logger(name)
	effective_level = min(
		console_level_value,
		file_level_value if file_level_value is not None else console_level_value
	)
	log.setLevel(effective_level)
	log.propagate = propagate

	fmt = formatter or logging.Formatter(
		"%(asctime)s [%(levelname)s] %(name)s: %(message)s"
	)

	has_stream = False
	for handler in log.handlers:
		if isinstance(handler, logging.StreamHandler):
			handler.setLevel(console_level_value)
			handler.setFormatter(fmt)
			has_stream = True
	if not has_stream:
		stream_handler = logging.StreamHandler()
		stream_handler.setLevel(console_level_value)
		stream_handler.setFormatter(fmt)
		log.addHandler(stream_handler)

	if file_path:
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		file_handler: logging.Handler
		if rotate:
			file_handler = RotatingFileHandler(
				path,
				mode=mode,
				maxBytes=max_bytes,
				backupCount=backup_count,
				encoding="utf-8"
			)
		else:
			file_handler = logging.FileHandler(path, mode=mode, encoding="utf-8")
		file_handler.setLevel(
			file_level_value if file_level_value is not None else console_level_value
		)
		file_handler.setFormatter(fmt)
		if not any(
				getattr(handler, "baseFilename", None) == str(path)
				for handler in log.handlers
		):
			log.addHandler(file_handler)

	return log
