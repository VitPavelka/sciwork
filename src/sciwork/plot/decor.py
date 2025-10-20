# src/sciwork/plot/decor.py
"""Legend and annotation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Tuple, Union

from ..logutil import get_logger
from .base import TickType, BasePlot

if TYPE_CHECKING:  # pragma: no cover - import for typing only
	from matplotlib.axes import Axes

LOG = get_logger(__name__)


class Decor(BasePlot):
	"""Helpers for grid lines, legends, and textual annotations."""
	def set_grid(
			self,
			*,
			color: str = "grey",
			alpha: float = 0.5,
			which: TickType = "both",
			linewidth: float = 1.0,
			linestyle: str = "--",
			axis: str = "both",
			ax: Optional["Axes"] = None,
	) -> "Axes":
		"""Enable Matplotlib grid lines."""

		if axis not in {"x", "y", "both"}:
			raise ValueError(f"axis must be 'x', 'y', or 'both'; got '{axis}'.")

		axes = self._axes_or_default(ax)
		axes.grid(True, which=which, axis=axis, color=color, alpha=alpha, linestyle=linestyle, linewidth=linewidth)
		return axes

	def set_legend(
			self,
			*,
			position: Union[str, Tuple[float, float]] = "best",
			alpha: float = 1.0,
			fontsize: float = 10.0,
			fontcolor: str = "black",
			order: Optional[Sequence[int]] = None,
			exclude_labels: Optional[Sequence[str]] = None,
			ax: Optional["Axes"] = None,
	) -> Optional["Axes"]:
		"""Display a legend with additional formatting controls."""

		axes = self._axes_or_default(ax)
		handles, labels = axes.get_legend_handles_labels()

		if order is not None:
			handles = [handles[idx] for idx in order if idx < len(handles)]
			labels = [labels[idx] for idx in order if idx < len(labels)]
		if exclude_labels:
			filtered = [(h, l) for h, l in zip(handles, labels) if l not in exclude_labels]
			if not filtered:
				LOG.warning("Legend request ignored: no labeled artists present.")
				return None
		if not handles:
			LOG.warning("Legend request ignored: no labeled artists present.")
			return None
		legend = axes.legend(handles, labels, loc=position, framealpha=alpha, fontsize=fontsize)
		for text in legend.get_texts():
			text.set_color(fontcolor)
		return axes

	def custom_text(
			self,
			text: str,
			*,
			position: Union[str, Tuple[float, float]] = "upper right",
			fontcolor: str = "black",
			fontsize: float = 10.0,
			style: Optional[str] = None,
			ha: str = "center",
			va: str = "center",
			ax: Optional["Axes"] = None,
	) -> "Axes":
		"""Insert arbitrary text in axes-relative coordinates."""

		axes = self._axes_or_default(ax)
		fontdict = {'fontsize': fontsize, 'color': fontcolor}
		if style:
			lowered = style.lower()
			if "bold" in lowered:
				fontdict['weight'] = "bold"
			if "italic" in lowered:
				fontdict['style'] = "italic"
		if isinstance(position, tuple):
			x, y = position
		else:
			mapping = {
				"upper right": (0.9, 0.9),
				"upper left": (0.1, 0.9),
				"lower left": (0.1, 0.1),
				"lower right": (0.9, 0.1),
				"center": (0.5, 0.5),
				"center left": (0.1, 0.5),
				"center right": (0.9, 0.5),
				"lower center": (0.5, 0.1),
				"upper center": (0.5, 0.9),
			}
			x, y = mapping.get(position, (0.5, 0.5))
		axes.text(x, y, text, transform=axes.transAxes, fontdict=fontdict, ha=ha, va=va)
		return axes
