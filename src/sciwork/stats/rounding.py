# src/sciwork/stats/rounding.py

from __future__ import annotations

import math

__all__ = ["normal_round"]


def normal_round(value: float, decimals: int = 0) -> float:
	"""
	Round using half-up semantics (0.5 → up), unlike NumPy's banker rounding.

	:param value: A value to round (mathematically correctly).
	:param decimals: The number of decimal places to round to.
	:return: Rounded value.
	:raises TypeError: If ``value`` is not a real number.
	:raises ValueError: If ``decimals`` is not a non-negative integer.
	"""
	if not isinstance(value, (int, float)):
		raise TypeError(f"value must be a real number, got {type(value)}")
	if not isinstance(decimals, int) or decimals < 0:
		raise ValueError(f"decimals must be a non-negative integer, got {decimals}")

	factor = 10 ** decimals
	v = value * factor
	frac = abs(v) - abs(math.floor(v))
	if frac < 0.5:
		return math.floor(v) / factor
	return math.ceil(v) / factor
