# src/sciwork/plot/layout.py
"""Axes labeling and layout helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union

from ..imports import matplotlib as mpl  # type: ignore

from .base import Axis, AxisSelector, BasePlot

if TYPE_CHECKING:  # pragma: no cover - import for static analysis
	from matplotlib.axes import Axes


class Layout(BasePlot):
	"""Methods adjusting axis labels, limits, and spine positions."""

	def set_plot_labels(
			self,
			*,
			ax: Optional["Axes"] = None,
			title: Optional[str] = None,
			xlabel: Optional[str] = None,
			ylabel: Optional[str] = None,
			zlabel: Optional[str] = None,
			xshift: float = 0.0,
			yshift: float = 0.0,
			zshift: float = 0.0,
			xt: float = 0.0,
			yt: float = 0.0
	) -> "Axes":
		"""Assign axis labels with optional relative offsets."""

		axes = self._axes_or_default(ax)

		if title:
			axes.set_title(title)
		if xlabel:
			axes.set_xlabel(xlabel)
			transform = mpl.transforms.Scaledtranslation(xshift, yt, self.fig.dpi_scale_trans)
			axes.xaxis.get_label().set_transform(axes.xaxis.get_label().get_transform() + transform)
		if ylabel:
			axes.set_ylabel(ylabel)
			transform = mpl.transforms.Scaledtranslation(xt, yshift, self.fig.dpi_scale_trans)
			axes.yaxis.get_label().set_transform(axes.yaxis.get_label().get_transform() + transform)
		if zlabel and hasattr(axes, "zaxis"):
			axes.set_zlabel(zlabel)
			transform = mpl.transforms.Scaledtranslation(0, zshift, self.fig.dpi_scale_trans)
			axes.zaxis.get_label().set_transform(axes.zaxis.get_label().get_transform() + transform)

		self.fig.canvas.draw_idle()
		return axes

	def toggle_dark_mode(self, dark_mode: bool = True, *, ax: Optional["Axes"] = None) -> "Axes":
		"""Switch background and text colors for the provided axes."""

		axes = self._axes_or_default(ax)
		background_color, element_color = ("black", "white") if dark_mode else ("white", "black")
		axes.set_facecolor(background_color)
		axes.figure.set_facecolor(background_color)
		axes.tick_params(colors=element_color, which='both')
		for spine in axes.spines.values():
			spine.set_edgecolor(element_color)
		axes.xaxis.label.set_color(element_color)
		axes.yaxis.label.set_color(element_color)
		if hasattr(axes, "zaxis"):
			axes.zaxis.label.set_color(element_color)
		axes.title.set_color(element_color)
		return axes

	def set_axes_linewidth(self, linewidth: float = 1.0, *, ax: Optional["Axes"] = None) -> "Axes":
		"""Set outline width for all axis spines."""

		axes = self._axes_or_default(ax)
		for spine in axes.spines.values():
			spine.set_linewidth(linewidth)
		return axes

	def set_axes_limits(
			self,
			*,
			ax: Optional["Axes"] = None,
			xmin: Optional[Union[float, str]] = None,
			xmax: Optional[Union[float, str]] = None,
			ymin: Optional[Union[float, str]] = None,
			ymax: Optional[Union[float, str]] = None,
			zmin: Optional[Union[float, str]] = None,
			zmax: Optional[Union[float, str]] = None
	) -> "Axes":
		"""Set axis ranges; use ``'data'`` to reuse stored data limits."""

		axes = self._axes_or_default(ax)

		def resolve(
				axis: Axis,
				value: Optional[Union[float, str]],
				extreme: Literal["min", "max"],
				current: Tuple[float, float]
		) -> float:
			if value == "data":
				limits = self._get_axis_limits(axis)
				selected = limits[0] if extreme == "min" else limits[1]
				if selected is None:
					raise ValueError(f"No stored data limits for axis {axis!r}.")
				return selected
			return current[0 if extreme == "min" else 1] if value is None else float(value)

		axes.set_xlim(
			left=resolve("x", xmin, "min", axes.get_xlim()),
			right=resolve("x", xmax, "max", axes.get_xlim())
		)
		axes.set_ylim(
			bottom=resolve("y", ymin, "min", axes.get_ylim()),
			top=resolve("y", ymax, "max", axes.get_ylim())
		)
		if hasattr(axes, "set_zlim"):
			axes.set_zlim(
				bottom=resolve("z", zmin, "min", axes.get_zlim()),
				top=resolve("z", zmax, "max", axes.get_zlim())
			)
		return axes

	def set_title_size(self, size: float = 14.0, *, ax: Optional["Axes"] = None) -> "Axes":
		"""Resize title text."""

		axes = self._axes_or_default(ax)
		axes.title.set_size(size)
		return axes

	def set_axis_label_size(
			self,
			size: float = 12.0,
			*,
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Resize axis label fonts."""

		axes = self._axes_or_default(ax)
		for target in self._iter_axes(axis):
			label = getattr(axes, f"{target}axis").get_label()
			label.set_size(size)
		return axes

	def set_axis_position(
			self,
			*,
			axis: Literal["x", "y"] = "y",
			position: float = 0.0,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Reposition a spine to a data coordinate on the opposing axis."""

		axes = self._axes_or_default(ax)
		if axis == "x":
			axes.spines['bottom'].set_position(('data', position))
			axes.spines['top'].set_visible(False)
			axes.spines['right'].set_visible(False)
		elif axis == "y":
			axes.spines['left'].set_position(('data', position))
			axes.spines['right'].set_visible(False)
			axes.spines['top'].set_visible(False)
		else:
			raise ValueError(f"axis must be 'x' or 'y'; got '{axis}'.")
		self.fig.canvas.draw_idle()
		return axes
