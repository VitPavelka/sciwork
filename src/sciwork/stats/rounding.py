# src/sciwork/stats/rounding.py

from __future__ import annotations

import math

__all__ = ["normal_round"]


def normal_round(value: float, decimals: int = 0) -> float:
	"""
	Round to ``decimals`` places treating negative and positive values symmetrically.

	The helper implements the classic "round half-up" rule on the absolute
	value and reapplies the original sign.
	As a result, ``±1.25`` both round to ``±1.3`` while ``±1.24`` become ``±1.2``.
	Compared to Python¨s :func:`round`, ties never fall toward the even neighbor,
	and negatives do not drift toward zero.

	:param value: Real number to round.
	:param decimals: Number of decimal places to keep (must be ``>=0``).
	:return: Rounded float.
	:raises TypeError: If ``value`` is not a real number.
	:raises ValueError: If ``decimals`` is not a non-negative integer.
	"""

	if not isinstance(value, (int, float)):
		raise TypeError(f"value must be a real number, got {type(value)}")
	if not isinstance(decimals, int) or decimals < 0:
		raise ValueError(f"decimals must be a non-negative integer, got {decimals}")

	factor = 10 ** decimals
	scaled = abs(value) * factor
	rounded = math.floor(scaled + 0.5)
	result = rounded / factor
	return math.copysign(result, value)
