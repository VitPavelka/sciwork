# src/sciwork/plot/ticks.py
"""Tick and axis scaling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Sequence

from ..imports import matplotlib as mpl  # type: ignore
from ..imports import numpy as np  # type: ignore

from .base import Axis, AxisSelector, TickType, BasePlot

if TYPE_CHECKING:  # pragma: no cover - import for static typing only
	from matplotlib.axes import Axes


class Ticks(BasePlot):
	"""Operations for tick appearance and axis scaling."""

	def set_ticks_linewidth(
			self,
			linewidth: float = 1.0,
			*,
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":

		axes = self._axes_or_default(ax)
		for target in self._iter_axes(axis):
			axes.tick_params(axis=target, which="both", width=linewidth)
		return axes

	def set_tick_length(
			self,
			length: float = 4.0,
			*,
			tick_type: TickType = "both",
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Update tick lengths for major/minor ticks on the selected axes."""

		axes = self._axes_or_default(ax)
		which = ["major", "minor"] if tick_type == "both" else [tick_type]
		for target in self._iter_axes(axis):
			for entry in which:
				axes.tick_params(axis=target, which=entry, length=length)
		return axes

	def set_tick_invisible(self, *, axis: AxisSelector = "both", ax: Optional["Axes"] = None) -> "Axes":
		"""Hide ticks and tick labels on the requested axes."""

		axes = self._axes_or_default(ax)
		for target in self._iter_axes(axis):
			params = {"axis": target, "which": "both", "length": 0}
			if target == "x":
				params.update({"labelbottom": False, "labeltop": False})
			elif target == "y":
				params.update({"labelleft": False, "labelright": False})
			else:
				params.update({"labelbottom": False})
			axes.tick_params(**params)
		return axes

	def set_minor_ticks(
			self,
			num_minor_ticks: int = 1,
			*,
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Configure additional minor ticks for linear or logarithmic axes."""

		if num_minor_ticks < 1:
			raise ValueError(f"num_minor_ticks must be >= 1; got {num_minor_ticks}.")

		axes = self._axes_or_default(ax)
		for target in self._iter_axes(axis):
			axis_obj = getattr(axes, f"{target}axis")
			if axis_obj.get_scale() == "log":
				subs = np.linspace(1, 10, num_minor_ticks + 1, endpoint=True)[1:]
				locator = mpl.ticker.LogLocator(base=10, subs=subs)
			else:
				locator = mpl.ticker.AutoMinorLocator(num_minor_ticks + 1)
			axis_obj.set_minor_locator(locator)
		return axes

	def set_custom_ticks(
			self,
			tick_values: Sequence[float],
			*,
			axis: Axis = "x",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Apply explicit tick positions for the given axis."""

		axes = self._axes_or_default(ax)
		getattr(axes, f"set_{axis}ticks")(tick_values)
		formatter = (
			mpl.ticker.LogFormatter()
			if getattr(axes, f"get_{axis}scale")() == "log"
			else mpl.ticker.ScalarFormatter()
		)
		getattr(axes, f"{axis}axis").set_major_formatter(formatter)
		return axes

	def set_custom_tick_labels(
			self,
			tick_labels: Sequence[str],
			*,
			axis: Axis = "x",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Assign textual labels to currently visible ticks."""

		axes = self._axes_or_default(ax)
		ticks = getattr(axes, f"get_{axis}ticks")()
		limits = getattr(axes, f"get_{axis}lim")()
		visible_ticks = [tick for tick in ticks if limits[0] <= tick <= limits[1]]
		if len(tick_labels) != len(visible_ticks):
			raise ValueError(
				f"Number of tick labels ({len(tick_labels)}) does not match visible ticks ({len(visible_ticks)})."
			)
		getattr(axes, f"set_{axis}tick")(visible_ticks)
		getattr(axes, f"{axis}axis").set_ticklabels(tick_labels)
		self.fig.canvas.draw_idle()
		return axes

	def set_log_scale(
			self,
			*,
			log_x: bool = False,
			log_y: bool = False,
			log_z: bool = False,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Switch axes to a logarithmic scale if requested."""

		axes = self._axes_or_default(ax)
		if log_x:
			axes.set_xscale("log")
		if log_y:
			axes.set_yscale("log")
		if log_z and hasattr(axes, "set_zscale"):
			axes.set_zscale("log")
		return axes

	def reverse_axis(
			self,
			*,
			reverse_x: bool = False,
			reverse_y: bool = False,
			reverse_z: bool = False,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Invert axis directions."""

		axes = self._axes_or_default(ax)
		if reverse_x:
			current = axes.get_xlim()
			axes.set_xlim(left=current[1], right=current[0])
		if reverse_y:
			current = axes.get_ylim()
			axes.set_ylim(bottom=current[1], top=current[0])
		if reverse_z and hasattr(axes, "set_zlim"):
			axes.set_zlim(axes.get_zlim()[::-1])
		return axes

	def scale_axis_labels(
			self,
			scale_factor: Optional[float] = None,
			*,
			method: Literal["simple", "order"] = "simple",
			axis: Axis = "x",
			is_log_scale: bool = False,
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Scale tick labels either by multiplication or orders of magnitude."""

		axes = self._axes_or_default(ax)
		if scale_factor is None:
			scale_factor = 0.0 if method == "order" else 1.0
		if method not in {"simple", "order"}:
			raise ValueError(f"method must be 'simple' or 'order'; got '{method}'.")

		multiplier = (10 ** scale_factor) if method == "order" else scale_factor

		if is_log_scale and multiplier <= 0:
			raise ValueError("Logarithmic scaling requires a positive multiplier.")

		def formatter(value: float, _pos: int) -> str:
			if is_log_scale:
				if value <= 0:
					return "0"
				exponent = np.log10(value) + np.log10(multiplier)
				if float(exponent).is_integer():
					return rf"$10^{{{int(round(exponent))}}}$"
				return rf"$10^{{{exponent:.2f}}}$"
			return f"{value * multiplier:g}"

		getattr(axes, f"{axis}axis").set_major_formatter(mpl.ticker.FuncFormatter(formatter))
		self.fig.canvas.draw_idle()
		return axes

	def set_tick_label_size(
			self,
			size: float = 10.0,
			*,
			axis: AxisSelector = "both",
			ax: Optional["Axes"] = None
	) -> "Axes":
		"""Resize tick label fonts, including offset text."""

		axes = self._axes_or_default(ax)
		for target in self._iter_axes(axis):
			axis_obj = getattr(axes, f"{target}axis")
			for label in axis_obj.get_ticklabels(which="both"):
				label.set_fontsize(size)
			axis_obj.get_offset_text().set_fontsize(size)
			if axis_obj.get_scale() == "log":
				axis_obj.set_major_formatter(mpl.ticker.LogFormatterMathtext())
		self.fig.canvas.draw_idle()
		return axes
