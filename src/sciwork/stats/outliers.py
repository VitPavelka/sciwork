# src/sciwork/stats/outliers.py

from __future__ import annotations

from typing import Optional, Union, List

from ..logutil import get_logger
from .coerce import DataLike, coerce_vector

from ..imports import numpy as np  # type: ignore

LOG = get_logger(__name__)

__all__ = ["outliers_iqr"]


def outliers_iqr(
		data: DataLike,
		*,
		column: Optional[Union[int, str]] = None,
		threshold: float = 1.5,
		max_iterations: int = 5
) -> np.ndarray:
	"""
	Identifies and filters outliers from a data set (1D vector) using the interquartile range (IQR) method.

	This function computes the first and third quartiles (Q1 and Q3) for the input data and then
	determines potential outliers as values falling below `Q1 - threshold * IQR` or above
	`Q3 + threshold * IQR`. It iteratively removes these outliers, updating the data and recalculating IQR
	up to a maximum number of iterations or until no outliers are identified. The detected outliers
	are returned as a numpy array.

	:param data: The input data to be analyzed for outliers.
	:param column: Specific column of the input data to analyze, only applicable if data is in a
	               format that supports column-based indexing (e.g., pd.DataFrame). Default is None.
	:param threshold: Multiplier for the IQR to define fences for detecting outliers. Default is 1.5.
	:param max_iterations: Maximum number of iterations to detect and remove outliers. Default is 5.
	:return: A numpy array containing the detected outliers (order preserved w.r.t. each pass).
	"""
	x = coerce_vector(data, column=column, dtype=float)
	x_work = x.copy()
	outs: List[float] = []
	try:
		for _ in range(max_iterations):
			q1, q3 = np.nanpercentile(x_work, [25, 75])
			iqr = q3 - q1
			lo, hi = q1 - threshold * iqr, q3 + threshold * iqr
			mask = (x_work < lo) | (x_work > hi)
			new_vals = x_work[mask]
			if new_vals.size == 0:
				break
			outs.extend(new_vals.tolist())
			x_work = x_work[~mask]
	except Exception as exc:
		LOG.error("outliers_iqr() failed: %s", exc)
		raise 
	return np.asarray(outs, dtype=float)
