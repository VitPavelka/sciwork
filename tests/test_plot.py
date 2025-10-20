# tests/test_plot.py

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

np = pytest.importorskip("numpy")
matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg", force=True)

from sciwork import Plot
from sciwork.imports import matplotlib as mpl  # type: ignore
from sciwork.stats import MathStat


@pytest.fixture()
def plot_instance():
	plot = Plot(figsize=(4, 3))
	try:
		yield plot
	finally:
		mpl.pyplot.close(plot.fig)


def test_plot_line_and_moving_average(plot_instance):
	plot = plot_instance
	x = np.arange(0, 10)
	y = np.linspace(0.0, 1.0, num=10)

	ax = plot.plot_2d(x, y, plot_type="line", label="line")
	plot.plot_2d(x, y, plot_type="moving_average", ma_window=3, label="avg", ax=ax)

	lines = ax.get_lines()
	assert len(lines) == 2
	np.testing.assert_allclose(lines[0].get_ydata(), y)

	expected_avg = MathStat(y).moving_average(window_size=3)
	np.testing.assert_allclose(lines[1].get_ydata(), expected_avg)

	legend_axes = plot.set_legend(ax=ax)
	assert legend_axes is ax


def test_plot_axes_limits_with_data_keyword(plot_instance):
	plot = plot_instance
	x = np.array([0, 1, 5, 10])
	y = np.array([2.0, 4.0, 1.0, 3.0])

	ax = plot.plot_2d(x, y, plot_type="line")
	plot.set_axes_limits(ax=ax, xmin="data", xmax="data", ymin="data", ymax="data")

	assert ax.get_xlim() == (0.0, 10.0)
	assert ax.get_ylim() == (1.0, 4.0)


def test_custom_tick_labels_validation(plot_instance):
	plot = plot_instance
	x = np.arange(0, 3)
	y = np.array([1.0, 2.0, 3.0])

	ax = plot.plot_2d(x, y, plot_type="line")
	with pytest.raises(ValueError):
		plot.set_custom_tick_labels(["one"], axis="x", ax=ax)
