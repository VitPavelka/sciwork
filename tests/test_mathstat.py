"""Integration tests for :class:`sciwork.stats.mathstat.MathStat`."""

from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")


from sciwork import MathStat, normal_round  # noqa: E402
from sciwork.stats import describe_1d, moving_average as moving_average_fn  # noqa: E402


def test_mathstat_1d_workflow_matches_function_equivalents():
	data = [1, 2, 3, 100]
	ms = MathStat(data)

	stats = ms.describe()
	expected_stats = describe_1d(data)
	for key, value in expected_stats.items():
		assert math.isclose(stats[key], value, rel_tol=1e-12, abs_tol=1e-12)

	pct = ms.percentiles([25, 50, 75])
	expected_pct = np.nanpercentile(np.asarray(data, dtype=float), [25, 50, 75])
	assert np.allclose(pct, expected_pct)

	out = ms.outliers(threshold=1.5)
	assert np.allclose(out, np.array([100.0]))

	assert np.allclose(ms.log(), np.log(np.asarray(data, dtype=float)))
	assert np.allclose(ms.power(base=10), np.power(10.0, np.asarray(data, dtype=float)))

	ma = ms.moving_average(window_size=3)
	expected_ma = moving_average_fn(data, window_size=3)
	assert np.allclose(ma, expected_ma)


def test_mathstat_dataframe_operations_and_table_summary():
	df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]})
	ms = MathStat(df)

	col_stats = ms.describe(column="b")
	assert math.isclose(col_stats["mean"], 4.0)
	assert math.isclose(col_stats["min"], 2.0)

	table = ms.describe_table()
	assert set(table.columns.get_level_values(0)) == {
		"min",
		"max",
		"sum",
		"mean",
		"median",
		"std",
		"coeff_var",
	}
	assert math.isclose(table[("sum", "b")], 12.0)
	assert math.isclose(table[("mean", "a")], 2.0)


def test_mathstat_describe_table_requires_dataframe():
	ms = MathStat([1, 2, 3])
	with pytest.raises(ValueError):
		ms.describe_table()


@pytest.mark.parametrize(
	("value", "decimals", "expected"),
	[
		(0.5, 0, 1.0),
		(1.25, 1, 1.3),
		(-1.25, 1, -1.3),
		(2.0, 0, 2.0),
	],
)
def test_normal_round_half_up(value: float, decimals: int, expected: float):
	assert math.isclose(normal_round(value, decimals), expected)
