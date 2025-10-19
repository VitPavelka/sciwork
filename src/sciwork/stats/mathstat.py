# src/sciwork/stats/mathstat.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union, Dict

from .coerce import coerce_vector
from .describe import describe_1d, describe_df, percentiles
from .outliers import outliers_iqr
from .transforms import moving_average, log_values, power_values

from ..imports import numpy as np  # type: ignore
from ..imports import pandas as pd  # type: ignore


@dataclass
class MathStat:
	"""
	Optional thin wrapper for stateful workflows.

	Examples
	--------
	>>> ms  = MathStat([1, 2, 3, 100])
	>>> ms.describe()
	{'min', 1.0, 'max': 100.0, 'sum': 106, 'mean': 26.5, ...}
	>>> ms.outliers(threshold=1.5)
	array([100.])

	Notes
	-----
	- `data` may be 1D (sequence/Series) or 2D (DataFrame). Most methods accept
	  an optional `column` for 2D inputs.
	- If you prefer stateless usage, call module-level functions instead.
	"""
	data: Any

	def vector(self, *, column: Optional[Union[int, str]] = None) -> np.ndarray:
		"""Return 1D numeric vector (np.ndarray) coerced from internal data."""
		return coerce_vector(self.data, column=column, dtype=float)

	# --- 1D Stats ---
	def describe(self, *, column: Optional[Union[int, str]] = None) -> Dict[str, float]:
		"""Return basic descriptive statistics for a 1D vector (NaN-aware)."""
		return describe_1d(self.data, column=column)

	def percentiles(self, pct: Iterable[float], *, column: Optional[Union[int, str]] = None) -> np.ndarray:
		"""Compute percentiles for a 1D vector (NaN-aware)."""
		return percentiles(self.data, pct, column=column)

	def outliers(self, *, column: Optional[Union[int, str]] = None, threshold: float = 1.5, max_iterations: int = 5) -> np.ndarray:
		"""Identifies and filters outliers from a data set (1D vector) using the interquartile range (IQR) method."""
		return outliers_iqr(self.data, column=column, threshold=threshold, max_iterations=max_iterations)

	# --- Transform ---
	def log(self, *, column: Optional[Union[int, str]] = None, base: float = np.e) -> np.ndarray:
		"""Compute the logarithm of a specified column or coerced vector from the input data using the given base."""
		return log_values(self.data, column=column, base=base)

	def power(self, *, column: Optional[Union[int, str]] = None, base: float = np.e) -> np.ndarray:
		"""Calculates the element-wise exponential of the input data based on the specified base."""
		return power_values(self.data, column=column, base=base)

	def moving_average(self, *, column: Optional[Union[int, str]] = None, window_size: int = 5, iterations: int = 1) -> np.ndarray:
		"""Compute the moving average of a specified column or coerced vector from the input data."""
		return moving_average(self.data, column=column, window_size=window_size, iterations=iterations)

	# --- DataFrame-wide describe ---
	def describe_table(self, *, axis: int = 0) -> pd.DataFrame:
		"""Return a DataFrame with descriptive statistics for each column of the input DataFrame."""
		if not isinstance(self.data, pd.DataFrame):  # type: ignore[attr-defined]
			raise ValueError(f"describe_table requires a pandas DataFrame as `data`: {type(self.data)}")
		return describe_df(self.data, axis=axis)
