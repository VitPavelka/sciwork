# src/sciwork/stats/transforms.py

from __future__ import annotations

import math
from typing import Optional, Union

from ..logutil import get_logger
from .coerce import DataLike, coerce_vector

from ..imports import numpy as np  # type: ignore

LOG = get_logger(__name__)

__all__ = ["log_values", "power_values", "moving_average"]


def log_values(data: DataLike, *, column: Optional[Union[int, str]] = None, base: float = math.e) -> np.ndarray:
	"""
	Compute the logarithm of a specified column or coerced vector from the input data using
	the given base. Values that result in invalid logarithmic computation (e.g., negative
	or zero input) will be handled gracefully as per NumPy rules.

	:param data: Input data which can be coerced into a numeric vector or
	    contains a column to extract.
	:param column: The column index/name to extract for logarithmic computation,
	    or ``None`` to use the data directly.
	:param base: The base of the logarithm to apply. Defaults to the natural logarithm (e).
	:return: An array of computed logarithmic values, with invalid results being
	    represented as NaN or negative infinity as per NumPy rules.
	"""
	x = coerce_vector(data, column=column, dtype=float)
	with np.errstate(divide="ignore", invalid="ignore"):
		out = np.log(x) / math.log(base)
	return out.astype(float, copy=False)


def power_values(data: DataLike, *, column: Optional[Union[int, str]] = None, base: float = math.e) -> np.ndarray:
	"""
	Calculates the element-wise exponential of the input data based on the specified base.

	This method accepts data in various formats, extracts the specified column if necessary,
	and computes the exponential of each element using the provided base. The result is
	returned as a NumPy array with floating-point values.

	:param data: Data in a compatible format, which can include NumPy arrays, Pandas DataFrames,
	    lists, or other data structures. It represents the source from which the exponential values
	    will be computed.
	:param column: An optional parameter that specifies the column (if applicable) to be used from the
	    input data. Can be an index or a column name. If not provided, the entire dataset or
	    default behavior will be used.
	:param base: The base of the exponential function. Defaults to `math.e` if not specified.
	:return: A NumPy array containing the computed exponential values with dtype `float`.
	"""
	x = coerce_vector(data, column=column, dtype=float)
	with np.errstate(over="ignore", invalid="ignore"):
		out = np.power(base, x)
	return out.astype(float, copy=False)


def moving_average(
		data: DataLike,
		*,
		column: Optional[Union[int, str]] = None,
		window_size: int = 5,
		iterations: int = 1
) -> np.ndarray:
	"""
	Computes the moving average of a numerical vector with a specified window size
	and number of iterations. The moving average is calculated using a
	convolution operation, where a kernel of uniform weights equal to 1/window_size
	is applied to the data vector iteratively. The data is padded using the
	"reflect" mode during the convolution process.

	The function accepts numerical vectors, with an optional argument to select
	a specific column of a structured or multidimensional input. It ensures
	that the `window_size` and `iterations` are strictly positive integers
	and validates that the window size does not exceed the length of the input vector.

	:param data: Input numerical data. Can be an array or a data structure that
	    can be coerced to a numerical vector.
	:param column: Optional selection of a specific column if the data
	    contains multiple dimensions or is structured. Defaults to None.
	:param window_size: Size of the moving window used in the convolution.
	    Must be a positive integer and should not exceed the length of the input vector.
	:param iterations: Number of times the moving average operation is repeated
	    on the data. Must be a positive integer.
	:return: A numpy array containing the computed moving average of the input data.
	:raises ValueError: If `window_size` or `iterations` are not positive integers,
	    or if `window_size` exceeds the length of the vector.
	:raises Exception: If the operation fails due to other unforeseen issues, logs
	    the error message and raises the exception.
	"""
	x = coerce_vector(data, column=column, dtype=float)
	if window_size < 1 or iterations < 1:
		raise ValueError("window_size and iterations must be positive integers.")
	if window_size > x.size:
		raise ValueError("window_size must not exceed the vector length.")

	out = x.astype(float, copy=True)
	try:
		kernel = np.ones(window_size, dtype=float) / window_size
		pad = window_size // 2
		for _ in range(iterations):
			padded = np.pad(out, pad, mode="reflect")
			conv = np.convolve(padded, kernel, mode="valid")
			out = conv
		return out
	except Exception as exc:
		LOG.exception("moving_average failed: %s", exc)
		raise
