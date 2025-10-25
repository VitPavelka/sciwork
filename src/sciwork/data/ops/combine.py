# src/sciwork/data/ops/combine.py

"""Column combination helpers for :class:`~sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from typing import List, Sequence, Optional, Literal

from ...imports import numpy as np  # type: ignore
from ...imports import pandas as pd  # type: ignore
from ...stats.outliers import outliers_iqr
from ..filters import _FilterAndLoadMixin

__all__ = ["Combine"]


class Combine(_FilterAndLoadMixin):
	"""Provide dataframe concatenation and row-level statistics."""

	def concatenate_column_from_dataframes(
			self,
			set_number: int,
			column_indices: Sequence[int],
			x_column: Optional[int] = None
	) -> pd.DataFrame:
		"""
		Concatenate selected columns from all frames in ``set_number``.

		:param set_number: Numeric identifier of the dataset to operate on.
		:param column_indices: Column positions (zero-based) to extract from
			every frame.
		:param x_column: Optional index copied verbatim as the first column
			(typically the shared x-axis). When ``None`` the result contains
			only the requested indices.
		:return: Combined dataframe whose columns are reindexed sequentially.
		:raises ValueError: If the dataset is empty or ``column_indices`` is
			empty.
		:raises IndexError: When any index exceeds the available columns in
			one of the frames.
		"""

		dataset = self.get_dataset(set_number)
		if not dataset.frames:
			raise ValueError(f"Set {set_number} is empty; load data first.")

		indices = list(dict.fromkeys(column_indices))
		if not indices:
			raise ValueError("column_indices must contain at least one entry.")

		pieces: List[pd.DataFrame] = []
		if x_column is not None:
			pieces.append(dataset.frames[0].iloc[:, [x_column]].copy())

		for frame in dataset.frames:
			if max(indices) >= frame.shape[1]:
				raise IndexError("column index out of range for frame")
			pieces.append(frame.iloc[:, indices].reset_index(drop=True))

		combined = pd.concat(pieces, axis=1, ignore_index=True)
		self.data_sets[dataset.name] = [combined]
		return combined

	@staticmethod
	def _coefficient_of_variation(arr: np.ndarray) -> float:
		if arr.size == 0:
			return float("nan")
		mean = float(np.mean(arr))
		if np.isclose(mean, 0.0):
			return float("nan")
		return float(np.std(arr, ddof=0) / mean)

	@staticmethod
	def _compute_row_statistics(
			values: pd.DataFrame,
			*,
			option: Literal["average", "sum", "min", "max", "std", "median", "coeff_var"],
			threshold: float
	) -> pd.Series:
		allowed = {
			"average": "mean",
			"sum": "sum",
			"min": "min",
			"max": "max",
			"std": "std",
			"median": "median",
			"coeff_var": "coeff_var"
		}
		if option not in allowed:
			raise ValueError(f"'option' must be one of {allowed.keys()}: {option}")

		filtered = values.apply(
			lambda row: outliers_iqr(row.astype(float), threshold=threshold), axis=1
		)

		computations = {
			"average": filtered.apply(np.mean),
			"sum": filtered.apply(np.sum),
			"min": filtered.apply(np.min),
			"max": filtered.apply(np.max),
			"std": filtered.apply(np.std, ddof=0),
			"median": filtered.apply(np.median),
			"coeff_var": filtered.apply()
		}

		series = computations[option]
		series = series.replace({np.inf: np.nan, -np.inf: np.nan})
		return series

	def rows_param_in_dataframe(
			self,
			set_number: int,
			column_indices: Sequence[int],
			*,
			option: Literal["average", "min", "max", "sum", "std", "median", "coeff_var"] = "average",
			threshold: float = 1.5,
			include_x_column: bool = True
	) -> pd.DataFrame:
		"""Compute per-row statistics across selected columns."""

		combined = self.concatenate_column_from_dataframes(
			set_number, column_indices, x_column=0 if include_x_column else None
		)

		values = combined.iloc[:, 1:] if include_x_column else combined
		result = self._compute_row_statistics(values, option=option, threshold=threshold)

		if include_x_column:
			output = pd.concat([combined.iloc[:, 0], result], axis=1)
			output.columns = [0, 1]
		else:
			output = result.to_frame(name=0)

		self.data_sets[f"Set {set_number}"] = [output]
		return output






