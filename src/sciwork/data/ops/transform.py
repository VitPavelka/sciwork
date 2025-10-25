# src/sciwork/data/ops/transform.py

"""Column transformation helpers for :class:`~sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from typing import Sequence, Literal

from ..filters import _FilterAndLoadMixin
from ...imports import numpy as np  # type: ignore
from ...imports import pandas as pd  # type: ignore
from ...stats.transforms import moving_average as _moving_average

__all__ = ["Transform"]


class Transform(_FilterAndLoadMixin):
	"""Provide logarithmic/power transforms and smoothing helpers."""

	def transform_columns(
			self,
			set_number: Sequence[int],
			column_indices: Sequence[int],
			base: float,
			*,
			transform_type: Literal["log", "power"] = "log"
	) -> None:
		"""Apply logarithmic or power transform to specified columns."""

		if transform_type not in {"log", "power"}:
			raise ValueError(f"'transform_type' must be 'log' or 'power': {transform_type}")

		for set_number in set_number:
			dataset = self.get_dataset(set_number)
			for frame in dataset.frames:
				for column in column_indices:
					if column >= frame.shape[1]:
						raise IndexError(f"column index is out of range.")
					data = frame.iloc[:, column].astype(float)
					if transform_type == "log":
						if base <= 0 or base == 1:
							raise ValueError(f"'base' must be greater than 0 and not equal to 1: {base}.")
						frame.iloc[:, column] = np.log(data) / np.log(base)
					else:
						frame.iloc[:, column] = np.power(base, data)

	def moving_average(
			self,
			set_number: int,
			column_index: int,
			*,
			window_size: int = 5,
			iterations: int = 1,
	) -> pd.Series:
		"""Compute a moving average for ``column_index`` within ``set_number``."""

		dataset = self.get_dataset(set_number)
		if not dataset.frames:
			raise ValueError(f"Set {set_number} has no frames loaded")

		frame = dataset.frames[0]
		if column_index >= frame.shape[1]:
			raise IndexError("'column_index' out of range")

		averaged = _moving_average(
			frame.iloc[:, column_index],
			column=None,
			window_size=window_size,
			iterations=iterations,
		)
		series = pd.Series(averaged)
		frame.iloc[:, column_index] = series.values
		return series
