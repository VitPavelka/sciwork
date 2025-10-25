# src/sciwork/data/ops/subtraction.py

"""Dataset subtraction helpers for :class:`~sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from typing import List, Sequence, Optional, Union

from ...imports import numpy as np  # type: ignore
from ..filters import _FilterAndLoadMixin

__all__ = ["Subtraction"]


class Subtraction(_FilterAndLoadMixin):
	"""Provide blank subtraction with optional segmentation."""

	@staticmethod
	def _get_segment_indices(x_values: Sequence[float], positions: Sequence[float]) -> List[int]:
		if not positions:
			return [0, len(x_values)]
		arr = np.array(x_values, dtype=float)
		if arr.ndim != 1:
			raise ValueError(f"'x_values' must be 1-dimensional, not {arr.ndim}-dimensional")
		diffs = np.diff(arr)
		if np.any(diffs == 0):
			raise ValueError("'x_values' must be strictly monotonic")
		increasing = np.all(diffs > 0)
		indices = [0]
		for position in positions:
			if increasing:
				idx = int(np.searchsorted(arr, position, side="right"))
			else:
				idx = int(np.searchsorted(arr[::-1], position, side="left"))
				idx = len(arr) - idx
			indices.append(idx)
		indices.append(len(arr))
		return indices

	def subtract_dataset(
			self,
			set_number: int,
			sub_set_number: int,
			columns_in_set: Sequence[int],
			sub_column: int,
			*,
			x_column: int = 0,
			positions: Optional[Sequence[float]] = None,
			fractions: Union[float, Sequence[float]]  = 1.0
	) -> None:
		"""Subtract a reference dataset from ``set_number``."""

		target = self.get_dataset(set_number)
		subtarget = self.get_dataset(sub_set_number)
		if not subtarget.frames:
			raise ValueError(f"The subtracted dataset {sub_set_number} has no data.")

		subtarget_frame = subtarget.frames[0]
		if sub_column >= subtarget_frame.shape[1]:
			raise IndexError(f"'sub_column' is out of range.")
		subtarget_data = subtarget_frame.iloc[:, sub_column].to_numpy(dtype=float)

		if positions is None or isinstance(fractions, (int, float)):
			fraction_value = float(fractions)
			for frame in target.frames:
				for column in columns_in_set:
					frame.iloc[:, column] = frame.iloc[:, column] - subtarget_data * fraction_value
			return

		if not isinstance(fractions, Sequence):
			raise TypeError(f"'fractions' must be a sequence when positions are provided : {type(fractions)}")
		if len(fractions) != len(positions) + 1:
			raise ValueError(f"'fractions' must have length len(positions) + 1)")

		for frame in target.frames:
			x_values = frame.iloc[:, x_column].to_numpy(dtype=float)
			indices = self._get_segment_indices(x_values, positions)
			for column in columns_in_set:
				data = frame.iloc[:, column].to_numpy(dtype=float)
				adjusted = np.zeros_like(data)
				previous_end = None
				for idx, (start, end) in enumerate(zip(indices[:-1], indices[1:])):
					fraction = float(fractions[idx])
					segment = data[start:end] - subtarget_data[start:end] * fraction
					if previous_end is not None and start < len(adjusted):
						delta = adjusted[previous_end - 1] - segment[0]
						segment = segment + delta
					adjusted[start:end] = segment
					previous_end = end
				frame.iloc[:, column] = adjusted
