# src/sciwork/stats/coerce.py
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional, Union, overload

from ..logutil import get_logger
from ..imports import numpy as np  # type: ignore
from ..imports import pandas as pd  # type: ignore

LOG = get_logger(__name__)

__all__ = ["DataLike", "coerce_vector"]

ArrayLike1D = Union[Sequence[float], "np.ndarray", "pd.Series"]  # type: ignore[name-defined]
DataLike = Union[ArrayLike1D, "pd.DataFrame", Mapping[str, float]]  # type: ignore[name-defined]


# --- Core Conversion Helpers ---
def _is_pandas_df(obj: Any) -> bool:
	return (pd is not None) and isinstance(obj, pd.DataFrame)  # type: ignore[attr-defined]


def _is_pandas_series(obj: Any) -> bool:
	return (pd is not None) and isinstance(obj, pd.Series)  # type: ignore[attr-defined]


def _ensure_numeric(a: "np.ndarray") -> "np.ndarray":
	"""Raise a user-friendly error if an array is not numeric."""
	if not np.issubdtype(a.dtype, np.number):
		raise ValueError(f"Expected numeric data, got dtype={a.dtype!r}")
	return a


def from_dataframe(
		df: "pd.DataFrame",
		column: Optional[Union[int, str]],
		dtype: Any
) -> "np.ndarray":  # type: ignore[name-defined]
	if df.shape[1] == 1 and column is None:
		arr = df.iloc[:, 0].to_numpy()
	else:
		if column is None:
			raise ValueError(
				f"DataFrame has {df.shape[1]} columns; please specify `column` (name or 0-based index)."
			)
		try:
			col = df.iloc[:, int(column)] if isinstance(column, int) else df[column]  # type: ignore[index]
		except Exception as exc:
			LOG.error("Failed to select column %r: %s", column, exc)
			raise ValueError(f"Invalid column selector: {column!r}") from exc
		arr = col.to_numpy()
	return _ensure_numeric(np.asarray(arr, dtype=dtype))


def _from_sequence(seq: Sequence[Any], dtype: Any) -> "np.ndarray":
	if len(seq) == 0:
		raise ValueError("Empty sequence is not valid.")
	return _ensure_numeric(np.asarray(list(seq), dtype=dtype))


def _from_nd_array(a: "np.ndarray", dtype: Any) -> "np.ndarray":
	if a.ndim == 0:
		raise ValueError("Scalar is not valid; expected 1D array-like")
	if a.ndim > 1:
		raise ValueError(f"Expected 1D array-like; got ndim={a.ndim}")
	if a.size == 0:
		raise ValueError("Empty array is not valid.")
	return _ensure_numeric(a.astype(dtype, copy=False))


def _from_mapping(mp: Mapping[str, Any], dtype: Any) -> "np.ndarray":
	if len(mp) == 0:
		raise ValueError("Empty mapping is not valid.")
	return _ensure_numeric(np.asarray(list(mp.values()), dtype=dtype))


@overload
def coerce_vector(
		data: DataLike, *, column: Optional[Union[int, str]] = None, dtype: Any = float
) -> "np.ndarray": ...


@overload
def coerce_vector(
		data: Mapping[str, float], *, column: Optional[Union[int, str]] = None, dtype: Any = float
) -> "np.ndarray": ...


def coerce_vector(
		data: DataLike,
		*,
		column: Optional[Union[int, str]] = None,
		dtype: Any = float,
) -> "np.ndarray":
	"""
	Convert various data containers to a 1D numpy array.

	Accepts: sequence/ndarray/Series/Dict/Mapping and a single-column DataFrame.
	For DataFrame with multiple columns you must specify `column` (name or index).
	Dict/Mapping values are used in the insertion order.

	:param data: Input data.
	:param column: Column selector when `data` is a DataFrame. If ``column`` is ``None`` and
				   DF has exactly one column, that column is used; otherwise ValueError.
	:param dtype: Numpy dtype to cast the result to (default float).
	:return: 1D numeric array.
	:raises ValueError: On empty input, unsupported type, multiple DF columns without `column`,
						or non-numeric data.
	"""
	if _is_pandas_series(data):
		arr = np.asarray(data, dtype=dtype)
		if arr.size == 0:
			raise ValueError("Input Series is empty.")
		return _ensure_numeric(arr)

	if _is_pandas_df(data):
		return from_dataframe(data, column, dtype)  # type: ignore[arg-type]

	if isinstance(data, np.ndarray):
		return _from_nd_array(data, dtype)

	if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
		return _from_sequence(data, dtype)

	if isinstance(data, Mapping):
		return _from_mapping(data, dtype)

	raise ValueError(f"Unsupported data type: {type(data)}")
