# src/sciwork/data/ops/scaling.py

"""Scaling and normalization helpers for :class:`~sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from typing import Sequence, Optional, Tuple

from ...imports import pandas as pd  # type: ignore
from ..filters import _FilterAndLoadMixin

__all__ = ["Scaling"]


class Scaling(_FilterAndLoadMixin):
	"""Provide scaling, normalization, and offset utilities."""

	# --- Helpers ---
	def _max_range_across_sets(
			self, set_numbers: Sequence[int], column_indices: Sequence[int]
	) -> float:
		max_range = 0.0
		for set_number in set_numbers:
			dataset = self.get_dataset(set_number)
			for frame in dataset.frames:
				for column in column_indices:
					series = frame.iloc[:, column].astype(float)
					span = float(series.max()) - float(series.min())
					max_range = max(max_range, span)
		return max_range

	def multiply_columns(
			self,
			set_number: int,
			factor: float,
			*,
			include_x_column: bool = False
	) -> None:
		"""Scale selected dataset columns by ``factor``."""

		if not isinstance(factor, (int, float)):
			raise TypeError(f"'factor' must be metric (int, float): {type(factor)}")

		dataset = self.get_dataset(set_number)
		for frame in dataset.frames:
			start = 0 if include_x_column else 1
			frame.iloc[:, start:] = frame.iloc[:, start:] * factor

	def normalize_data(
			self,
			*,
			column_indices: Optional[Sequence[int]],
			set_numbers: Optional[Sequence[int]] = None,
			reference_data: Optional[Tuple[int, int, int]] = None,
			new_min_max: Tuple[float, float] = (0.0, 1.0),
	) -> None:
		"""Normalize selected columns to a given ``(min, max)`` range."""

		target_sets = self._resolve_set_numbers(set_numbers)
		if reference_data:
			ref_set, ref_df, ref_col = reference_data
			ref_dataset = self.get_dataset(ref_set)
			reference_frame = ref_dataset.frames[ref_df]
			series = reference_frame.iloc[:, ref_col].astype(float)
			new_min_max = (float(series.min()), float(series.max()))

		for key in target_sets:
			frames = self.data_sets.get(key, [])
			for frame in frames:
				for column in column_indices:
					series = frame.iloc[:, column].astype(float)
					min_val, max_val = new_min_max
					span = max_val - min_val
					if span == 0:
						raise ValueError("Normalization range span ('new_min_max' subtraction) must be non-zero.")
					current_span = float(series.max()) - float(series.min())
					if current_span == 0:
						continue
					normalized = (series - series.min()) / current_span
					frame.iloc[:, column] = normalized * span + min_val

	def factorize_data(
			self,
			set_numbers: Sequence[int],
			column_indices: Sequence[int],
			*,
			discrete_factorization: bool = False,
			scaling_factor: float = 1.0
	) -> float:
		"""Apply cumulative offsets to columns for stacked visualization."""

		total_offset = 0.0
		max_range = 0.0
		if discrete_factorization:
			max_range = self._max_range_across_sets(set_numbers, column_indices)

		for set_number in set_numbers:
			dataset = self.get_dataset(set_number)
			for frame in dataset.frames:
				for column in column_indices:
					if discrete_factorization:
						offset = total_offset
						total_offset += max_range * scaling_factor
					else:
						column_max = float(frame.iloc[:, column].max())
						offset = total_offset
						total_offset = (column_max + total_offset) * scaling_factor
					frame.iloc[:, column] = frame.iloc[:, column] + offset

		return total_offset if not discrete_factorization else len(set_numbers) * max_range * scaling_factor

	def add_value_to_columns(
			self,
			set_numbers: Sequence[int],
			column_indices: Sequence[int],
			value: float
	) -> None:
		"""Add ``value`` to each selected column across ``set_numbers``."""

		for set_number in set_numbers:
			dataset = self.get_dataset(set_number)
			for frame in dataset.frames:
				for column in column_indices:
					frame.iloc[:, column] = frame.iloc[:, column] + value
