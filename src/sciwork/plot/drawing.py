# src/sciwork/plot/drawing.py

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Dict, Union

from .base import PlotKind, BasePlot
from ..stats import MathStat

if TYPE_CHECKING:  # pragma: no cover - import for typing only
	from matplotlib.axes import Axes


class Drawing(BasePlot):
	"""Collection of drawing primitives used by :class:`~sciwork.plot.Plot`."""

	def draw_horizontal_line(
			self,
			y: float,
			*,
			color: str = "black",
			linewidth: float = 2.0,
			linestyle: str = "-",
			label: Optional[str] = None,
			alpha: float = 1.0,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Add a horizontal line."""

		axes = self._axes_or_default(ax)
		axes.axhline(y=y, color=color, linewidth=linewidth, linestyle=linestyle, label=label, alpha=alpha)
		return axes

	def draw_vertical_line(
			self,
			x: float,
			*,
			color: str = "black",
			linewidth: float = 2.0,
			linestyle: str = "-",
			label: Optional[str] = None,
			alpha: float = 1.0,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Add a vertical line."""

		axes = self._axes_or_default(ax)
		axes.axvline(x=x, color=color, linewidth=linewidth, linestyle=linestyle, label=label, alpha=alpha)
		return axes

	def plot_std_deviation(
			self,
			x: Sequence[float],
			y: Sequence[float],
			yerr: Sequence[float],
			*,
			color: str = "gray",
			alpha: float = 0.6,
			linewidth: float = 2.0,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Plot error bars representing a standard deviation envelope."""

		axes = self._axes_or_default(ax)
		axes.errorbar(
			x,
			y,
			yerr=yerr,
			fmt="",
			color=color,
			alpha=alpha,
			ecolor=color,
			capsize=4,
			linewidth=0,
			elinewidth=linewidth
		)
		self._update_limits(x, y)
		return axes

	def plot_1d(self, data: Sequence[float], *, ax: Optional["Axes"] = None) -> "Axes":
		"""Plot a simple 1D series against its index."""

		axes = self._axes_or_default(ax)
		axes.plot(data)
		self._update_limits(range(len(data)), data)
		return axes

	def plot_2d(
			self,
			x: Sequence[float],
			y: Sequence[float],
			*,
			plot_type: PlotKind = "line",
			ax: Optional["Axes"] = None,
			color: Optional[str] = None,
			alpha: float = 1.0,
			label: Optional[str] = None,
			linewidth: float = 2.0,
			linestyle: str = "-",
			markersize: float = 20.0,
			markertype: str = "o",
			ma_window: int = 5,
			ma_iterations: int = 1,
			bar_width: float = 0.8,
			edgecolor: Optional[str] = None,
			zorder: Optional[int] = None
	) -> "Axes":
		"""Render diverse 2D visualisations (line, scatter, moving average, histogram, bar)."""

		axes = self._axes_or_default(ax)
		params: Dict[str, Union[float, str]] = {'alpha': alpha, 'zorder': zorder}
		if color is not None:
			params['color'] = color
		if label is not None:
			params['label'] = label

		if plot_type in {"scatter", "line", "moving_average", "histogram", "bar"} and y is None:
			raise ValueError(f"Plot type {plot_type} requires y data.")

		if plot_type == "scatter":
			params.update({"s": markersize, "marker": markertype})
			axes.scatter(x, y, **params)

		elif plot_type == "line":
			params.update({"linewidth": linewidth, "linestyle": linestyle})
			axes.plot(x, y, **params)

		elif plot_type == "moving_average":
			params.update({"linewidth": linewidth, "linestyle": linestyle})
			smoothed = MathStat(y).moving_average(window_size=ma_window, iterations=ma_iterations)
			axes.plot(x, smoothed, **params)

		elif plot_type in {"histogram", "bar"}:
			params.update({"edgecolor": edgecolor})
			axes.bar(x, y, width=bar_width, align='center', **params)
		else:
			raise ValueError(f"Unsupported plot type: {plot_type}.")

		self._update_limits(x, y if y is not None else x)
		axes.relim()
		axes.autoscale_view()
		return axes

	def plot_3d(
			self,
			x: Sequence[float],
			y: Sequence[float],
			z: Sequence[float],
			*,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Create a 3D scatter plot (creates 3D axes if necessary)."""

		axes = ax
		if axes is None:
			axes = self.fig.add_subplot(111, projection="3d")
		axes.scatter(x, y, z)
		self._update_limits(x, y, z)
		return axes
