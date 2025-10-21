# src/sciwork/plot/layout.py
"""Axes labeling and layout helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union, cast

from ..imports import matplotlib as mpl  # type: ignore

from .base import Axis, AxisSelector, BasePlot

if TYPE_CHECKING:  # pragma: no cover - import for static analysis
	from matplotlib.axes import Axes
	from mpl_toolkits.mplot3d import Axes3D


class Layout(BasePlot):
	"""Methods adjusting axis labels, limits, and spine positions."""

	@staticmethod
	def _set_spine_position(axes: "Axes", spine: str, position: float) -> None:
		"""Position a spine against a data coordinate without type warnings."""
		spine_obj = axes.spines[spine]
		set_position = getattr(spine_obj, "set_position")
		set_position(("data", position))

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
		"""
		Assign axis labels to each axis and optionally shift their positions.

		:param ax: Axes instance to modify.
			When ``None`` the default plot axes are used.
		:param title: The plot title.
		:param xlabel: X-label of the plot.
		:param ylabel: Y-label of the plot.
		:param zlabel: Z-label of the plot.
		:param xshift: Normalized horizontal shift of X-label.
		:param yshift: Normalized vertical shift of Y-label.
		:param zshift: Normalized shift along the Z-axis.
		:param xt: Additional vertical shift for X-label.
		:param yt: Additional horizontal shift for Y-label.
		:return: The axes that received the updates.
		:raises AttributeError: If ``zlabel`` is provided for 2D axes without a z-axis.
		"""

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
		if zlabel:
			if not hasattr(axes, "zaxis"):
				raise AttributeError("zlabel requires a 3D axes.")
			axes3d = cast("Axes3D", axes)
			axes3d.set_zlabel(zlabel)
			transform = mpl.transforms.Scaledtranslation(0, zshift, self.fig.dpi_scale_trans)
			axes3d.zaxis.get_label().set_transform(axes3d.zaxis.get_label().get_transform() + transform)

		self.fig.canvas.draw_idle()
		return axes

	def toggle_dark_mode(self, dark_mode: bool = True, *, ax: Optional["Axes"] = None) -> "Axes":
		"""
		Switch between light and dark color schemes.

		:param dark_mode: When `True`` enable a dark background with light foreground
			colors; otherwise revert to light mode.
		:param ax: Axes to update; defaults to the primary axes.
		:return: The axes after color adjustments.
		"""

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
			cast("Axes3D", axes).zaxis.label.set_color(element_color)
		axes.title.set_color(element_color)
		return axes

	def set_axes_linewidth(self, linewidth: float = 1.0, *, ax: Optional["Axes"] = None) -> "Axes":
		"""
		Update the thickness of the axes' spines.

		:param linewidth: Width applied to the axes' spines.
		:param ax: Target axes to modify, defaults to the primary axes.
		:return: The axes after linewidth updates.
		"""

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
		"""
		Set numeric boundaries for each axis.

		:param ax: Axes to update; defaults to the primary axes.
		:param xmin: X-axis minimum.
		:param xmax: X-axis maximum.
		:param ymin: Y-axis minimum.
		:param ymax: Y-axis maximum.
		:param zmin: Z-axis minimum.
		:param zmax: Z-axis maximum.
		:return: The axes with updated limits.
		:raises ValueError: When ``"data"`` is specified but no limits are available.
		:raises AttributeError: If z-axis limits are requested on a 2D axes.
		"""

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
			axes3d = cast("Axes3D", axes)
			axes3d.set_zlim(
				bottom=resolve("z", zmin, "min", axes3d.get_zlim()),
				top=resolve("z", zmax, "max", axes3d.get_zlim())
			)
		return axes

	def set_title_size(self, size: float = 14.0, *, ax: Optional["Axes"] = None) -> "Axes":
		"""
		Resize the title font.

		:param size: Target font size in points.
		:param ax: Axes containing the title.
			Default to the primary axes.
		:return: The axes with updated title size.
		"""

		axes = self._axes_or_default(ax)
		axes.title.set_fontsize(size)
		return axes

	def set_axis_label_size(
			self,
			size: float = 12.0,
			*,
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""
		Change the font size for one or more axis labels.

		:param size: Font size to the selected labels.
		:param axis: Selector describing which axes should change ("x", "y", "z",
			"both", or "all").
		:param ax: Axes to modify; defaults to the instance axes.
		:return: The axes with resized labels.
		"""

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
		"""
		Reposition a spine to a data coordinate on the opposing axis.

		:param axis: Which axis to reposition ("x" or "y").
		:param position: The coordinate on the opposite axis where the spine should cross.
		:param ax: Axes to update.
			Defaults to the plot's primary axes.
		:return: The axes with updated spine placement.
		:raises ValueError: If ``axis`` is not "x" or "y".
		"""

		axes = self._axes_or_default(ax)
		if axis == "x":
			self._set_spine_position(axes, "bottom", position)
			axes.spines['top'].set_visible(False)
			axes.spines['right'].set_visible(False)
		elif axis == "y":
			self._set_spine_position(axes, "left", position)
			axes.spines['right'].set_visible(False)
			axes.spines['top'].set_visible(False)
		else:
			raise ValueError(f"axis must be 'x' or 'y'; got '{axis}'.")
		self.fig.canvas.draw_idle()
		return axes
