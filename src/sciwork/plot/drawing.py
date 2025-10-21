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
		"""
		Add a horizontal line across the axes.

		:param y: Y coordinate where the line should be drawn.
		:param color: Color styling parameter.
		:param linewidth: Line width styling parameter.
		:param linestyle: Line style styling parameter.
		:param label: Optional line label.
		:param alpha: Opacity of the line.
		:param ax: Axes to draw on.
			Defaults to the primary axes.
		:return: The axes that contain the new line.
		"""

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
		"""
		Add a vertical line across the axes.

		:param x: X coordinate for the line.
		:param color: Color styling parameter.
		:param linewidth: Line width styling parameter.
		:param linestyle: Line style styling parameter.
		:param label: Optional line label.
		:param alpha: Opacity of the line.
		:param ax: Axes to draw on.
			Defaults to the primary axes.
		:return: The axes that contain the new line.
		"""

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
		"""
		Plot error bars representing a standard deviation envelope.

		:param x: X coordinates for the error bars.
		:param y: Y coordinates for the error bars.
		:param yerr: Symmetric deviations for each point; forwarded to
			:func:`matplotlib.axes.Axes.errorbar`.
		:param color: Base color of the error bars.
		:param alpha: Opacity of the error bars.
		:param linewidth: Thickness of the error lines.
		:param ax: Axes to draw on. Defaults to the primary axes.
		:return: The axes that contain the error bars.
		:raises ValueError: If the input sequences differ in length.
		"""
		if not (len(x) == len(y) == len(yerr)):
			raise ValueError(f"x, y, and yerr must share identical lengths: "
			                 f"x={len(x)}, y={len(y)}, yerr={len(yerr)}")

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
		"""
		Plot a simple 1D series against its index.

		:param data: Iterable of numeric values.
		:param ax: Axes to draw on.
			Defaults to the primary axes.
		:return: The axes that contain the line plot.
		"""

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
		"""
		Render diverse 2D visualizations (line, scatter, moving average, histogram, bar).

		:param x: X-coordinates of the observations.
		:param y: Y-coordinates of the observations.
			Must be provided for all built-in plot types.
		:param plot_type: One of ``"line"``, ``"scatter"``, ``"moving_average"``, ``"histogram"``, or ``"bar"``.
		:param ax: Axes to draw on.
			Defaults to the primary axes.
		:param color: Color of the data visualization.
		:param alpha: Opacity of the data visualization.
		:param label: Label for the legend.
		:param linewidth: Line width of the data visualization.
			Applies to ``"line"`` and ``"moving_average"`` plot types.
		:param linestyle: Line style of the data visualization.
			Applies to ``"line"`` and ``"moving_average"`` plot types.
		:param markersize: Size of the markers in ``"scatter"`` plots.
		:param markertype: Type of the markers in ``"scatter"`` plots.
		:param ma_window: Size of the moving window used in the ``"moving_average"`` convolution.
		:param ma_iterations: Iteration count for the ``"moving_average"`` convolution.
		:param bar_width: Width of the bars in ``"bar"`` and ``"histogram"`` plots.
		:param edgecolor: Edge color of the bars in ``"bar"`` and ``"histogram"`` plots.
		:param zorder: Z-order of the visualization (rendering order).
		:return: The axes that contain the visualization.
		:raises ValueError: If required data is missing, or ``plot_type`` is unsupported.
		"""

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
		"""
		Create a 3D scatter plot (creates 3D axes if necessary).

		:param x: X-coordinates of the observations.
		:param y: Y-coordinates of the observations.
		:param z: Z-coordinates of the observations.
		:param ax: Existing 3D axes.
			When ``None``, a new subplot is created.
		:return: The 3D axes containing the scatter plot.
		:raises ValueError: If the coordinate sequences differ in length.
		"""
		if not (len(x) == len(y) == len(z)):
			raise ValueError(f"x, y, and z must share identical lengths: x={len(x)}, y={len(y)}, z={len(z)}")

		axes = ax
		if axes is None:
			axes = self.fig.add_subplot(111, projection="3d")
		axes.scatter(x, y, z)
		self._update_limits(x, y, z)
		return axes
