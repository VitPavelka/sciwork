# src/sciwork/imports/lazyproxy.py

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any, Optional

__all__ = ["LazyModule", "lazy_module"]


class LazyModule:
	"""
	Lightweight proxy that imports a module on first attribute access.

	Notes
	-----
	* Import happens on first attribute access.
	* If the module is not installed, raises an ImportError with a friendly hint.
	* For type checkers use ``if TYPE_CHECKING: import numpy as np`` in your modules.
	"""
	def __init__(
			self,
			name: str,
			*,
			install: Optional[str] = None,
			reason: Optional[str] = None
	) -> None:
		self._name = name
		self._mod: Optional[ModuleType] = None
		self._install = install
		self._reason = reason

	def _load(self) -> ModuleType:
		if self._mod is None:
			try:
				self._mod = importlib.import_module(self._name)
			except Exception as exc:
				parts = [f"Dependency module '{self._name}' is not installed."]
				if self._reason:
					parts.append(f"Needed for {self._reason}.")
				if self._install:
					parts.append(f"Install with '{self._install}'.")
				raise ImportError(" ".join(parts)) from exc
		return self._mod

	def __getattr__(self, item: str) -> Any:
		mod = self._load()
		# 1) try the module directly
		try:
			return getattr(mod, item)
		except AttributeError:
			pass

		# 2) fallback: try to import a submodule
		full_name = f"{self._name}.{item}"
		try:
			submod = importlib.import_module(full_name)
		except Exception as exc:
			# if the submodule is not found, keep the python behavior: AttributeError
			raise AttributeError(
				f"Module '{self._name!r} has no attribute '{item!r}'"
				f"and importing submodule {full_name!r} failed."
			) from exc

		# cache: next time through getattr(mod, item)
		setattr(mod, item, submod)
		return submod

	def __repr__(self) -> str:
		state = "not loaded" if self._mod is None else f"loaded={self._mod!r}"
		return f"<LazyModule name={self._name!r} {state}>"


def lazy_module(
		name: str, *, install: Optional[str] = None, reason: Optional[str] = None
) -> LazyModule:
	"""
	Create a lazy module proxy.

	:param name: Fully qualified module name.
	:param install: Optional installation hint for friendly ImportError.
	:param reason: Optional context why the dependency is needed.
	:return: :class:`LazyModule` instance.
	"""
	return LazyModule(name, install=install, reason=reason)
