# src/sciwork/data/handler.py

"""Public DataHandler implementation built on modular mixins."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Iterable, Optional, Union

from ..logutil import get_logger
from .config import DataHandlerConfig, bootstrap_data_handler_config
from .ops import DataOps

LOG = get_logger(__name__)

PathLike = Union[str, Path]


class DataHandler(DataOps):
	"""High-level utility for batch dataframe manipulation."""

	def __init__(
			self,
			config: Optional[DataHandlerConfig] = None,
			*,
			auto_load: bool = True,
			**legacy_kwargs
	) -> None:
		"""
		Create a handler either from a structured config or legacy kwargs.

		:param config: Parsed :class:`DataHandlerConfig`. When omitted, ``legacy_kwargs``
			are interpreted in the legacy string format and converted on the fly.
		:param auto_load: When ``True`` (default), files are immediately filtered and loaded
			into memory.
		:param legacy_kwargs: ``data_folderpath`` plus optional keyword strings matching the
			original utility signature (``general_keywords``, ``keywords``,
				``header_rows`` ...).
		:raises ValueError: If neither ``config`` nor ``data_folderpath`` is supplied.
		"""
		if config is None:
			if "data_folderpath" not in legacy_kwargs:
				raise ValueError("'data_folderpath' must be provided.")
			config = DataHandlerConfig.from_strings(**legacy_kwargs)
		super().__init__(config)
		if auto_load:
			self.filter_datafiles()
			self.data_loader()

	@classmethod
	def from_ini(
			cls,
			path: PathLike,
			*,
			section: str = "data",
			auto_load: bool = True
	) -> "DataHandler":
		"""
		Construct a handler from an INI configuration file.

		:param path: Path to the INI file produced via
			:func:`bootstrap_configs`.
		:param section: INI section containing the data handler options (default ``"data"``).
		:param auto_load: Forwarded to :meth:`__init__`.
		:return: Instance configured according to the INI section.
		:raises KeyError: If the requested section is missing.
		"""
		parser = configparser.ConfigParser()
		path = Path(path)






