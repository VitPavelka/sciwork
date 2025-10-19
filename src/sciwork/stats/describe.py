# src/sciwork/stats/describe.py

from __future__ import annotations

from typing import Iterable, Optional, Union, Dict

from ..logutil import get_logger
from .coerce import DataLike, coerce_vector

from ..imports import numpy as np  # type: ignore
from ..imports import pandas as pd  # type: ignore

LOG = get_logger(__name__)

__all__ = ["describe_1d", "describe_df", "percentiles"]


def describe_1d(data: DataLike, *, column: Optional[Union[int, str]] = None) -> Dict[str, float]:
	"""
	Basic descriptive statistics for a 1D vector (NaN-aware).

	:param data: Data for description.
	:param column: Column name or index for DataFrame.
	:return: min, max, sum, mean, median, std (ddof=1), coeff_var (std/mean).
	"""
	x = coerce_vector(data, column=column, dtype=float)
	with np.errstate(all="ignore"):
		mn = float(np.nanmin(x))
		mx = float(np.nanmax(x))
		sm = float(np.nansum(x))
		mean = float(np.nanmean(x))
		med = float(np.nanmedian(x))
		std = float(np.nanstd(x, ddof=1))
		coeff = float(std / mean) if mean not in (0.0, -0.0) else float("nan")
	return {"min": mn, "max": mx, "sum": sm, "mean": mean, "median": med, "std": std, "coeff_var": coeff}


def describe_df(df: pd.DataFrame, *, axis: int = 0) -> pd.DataFrame:
	"""
	Column/row-wise descriptive statistics for a DataFrame.

	:param df: DataFrame to describe.
	:param axis: The axis to describe (0=columns, 1=rows).
	:return: min, max, sum, mean, median, std (ddof=1), coeff_var (std/mean).
	"""
	if pd is None or not isinstance(df, pd.DataFrame):  # type: ignore[attr-defined]
		raise ValueError("describe_df requires a pandas DataFrame as input")
	agg = {
		"min": np.nanmin,
		"max": np.nanmax,
		"sum": np.nansum,
		"mean": np.nanmean,
		"median": np.nanmedian,
		"std": lambda a: np.nanstd(a, ddof=1),
	}
	out = {}
	try:
		for k, fn in agg.items():
			out[k] = df.aggregate(fn, axis=axis)  # type: ignore[arg-type]
		coeff = out["std"] / out["mean"]
		out["coeff_var"] = coeff.replace([np.inf, -np.inf], np.nan)
		return pd.concat(out, axis=1)  # type: ignore[return-value]
	except Exception as exc:
		LOG.exception("describe_df failed (axis=%s): %s", axis, exc)
		raise


def percentiles(data: DataLike, pct: Iterable[float], *, column: Optional[Union[int, str]] = None) -> np.ndarray:
	"""Compute percentiles for a 1D vector (NaN-aware)."""
	x = coerce_vector(data, column=column, dtype=float)
	return np.nanpercentile(x, list(pct))
