# src/sciwork/data/ops/selection.py

"""Row selection helpers for :class:`~sciwork.data.handler.DataHandler`."""

from __future__ import annotations

from typing import Sequence, Optional

from ...imports import pandas as pd  # type: ignore
from ..filters import _FilterAndLoadMixin

__all__ = ["Selection"]


class Selection(_FilterAndLoadMixin):
	"""Provide helpers to keep only rows within requested bounds."""

	def crop_data(
			self,
			column_index: int,
			range_min: float,
			range_max: float,
			*,
			set_numbers: Optional[Sequence[int]] = None
	) -> None:
		"""Trim rows outside ``[range_min, range_max]`` on ``column_index``."""

		targets = self._resolve_set_numbers(set_numbers)
		for key in targets:
			frames = self.data_sets.get(key, [])
			updated: list[pd.DataFrame] = []
			for df in frames:
				mask = df.iloc[:, column_index].between(range_min, range_max)
				updated.append(df.loc[mask].reset_index(drop=True))
			self.data_sets[key] = updated
