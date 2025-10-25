# src/sciwork/data/ops/__init__.py

"""Composable data operations mixins for :mod:`sciwork.data`."""

from __future__ import annotations

from .combine import Combine
from .scaling import Scaling
from .selection import Selection
from .subtraction import Subtraction
from .transform import Transform

__all__ = ["DataOps"]


class DataOps(
	Subtraction,
	Scaling,
	Transform,
	Selection,
	Combine
):
	"""Aggregate mixin exposing all dataframe helpers."""
