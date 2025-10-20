# src/sciwork/plot/base.py
"""Shared building blocks for :class:`~sciwork.plot.Plot`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Literal, Optional, Sequence, Tuple, Union

from ..imports import numpy as np  # type: ignore
from ..imports import pyplot as plt  # type: ignore
from ..logutil import get_logger

if TYPE_CHECKING:  # pragma: no cover - only for static typing
	from matplotlib.axes import Axes
	from matplotlib.figure import Figure

Axis = Literal["x", "y", "z"]
AxisSelector = Literal["x", "y", "z", "both", "all"]
TickType = Literal["major", "minor", "both"]
PlotKind = Literal["scatter", "line", "moving_average", "histogram", "bar"]

LOG = get_logger(__name__)


@dataclass
class _DataLimits:
	"""Mutable holder for running min/max values along each axis."""

	x: List[Optional[float]]
	y: List[Optional[float]]
	z: List[Optional[float]]

	@classmethod
	def empty(cls) -> "_DataLimits":
		return cls(x=[None, None], y=[None, None], z=[None, None])

	def update(self, axis: str, values: Sequence[float]) -> None:
		arr = np.asarray(values, dtype=float)
		arr = arr[~np.isnan(arr)]
		if arr.size == 0:
			return
		minimum = float(np.nanmin(arr))
		maximum = float(np.nanmax(arr))
		limits = getattr(self, axis)
		limits[0] = minimum if limits[0] is None else min(limits[0], minimum)
		limits[1] = maximum if limits[1] is None else max(limits[1], maximum)


class BasePlot:
	"""Provide figure lifecycle management and shared helpers."""

	def __init__(self, figsize: Tuple[float, float] = (9, 6)) -> None:
		self.figsize = figsize
		self.fig, self.ax = plt.subplots(figsize=figsize)
		self._limits = _DataLimits.empty()
		LOG.debug("Initialized Plot with figsize=%s", self.figsize)

	# --- Helpers ---
	def _axes_or_default(self, ax: Optional["Axes"]) -> "Axes":
		if ax is not None:
			return ax
		if self.ax is None:
			raise RuntimeError("Default axes missing; create a subplot first.")
		return self.ax

	def _update_limits(
			self,
			x: Optional[Sequence[float]],
			y: Optional[Sequence[float]] = None,
			z: Optional[Sequence[float]] = None
	) -> None:
		for axis_name, values in (("x", x), ("y", y), ("z", z)):
			if values is None:
				continue
			self._limits.update(axis=axis_name, values=values)

	def _get_axis_limits(self, axis: Axis) -> Tuple[Optional[float], Optional[float]]:
		stored = getattr(self._limits, axis)
		return stored[0], stored[1]

	@staticmethod
	def _iter_axes(selector: AxisSelector) -> Union[Sequence[Literal["x", "y", "both"]], Sequence[Literal["x", "y", "z", "all"]]]:
		if selector == "both":
			return "x", "y"
		if selector == "all":
			return "x", "y", "z"
		return (selector,)

	# --- Common utilities ---
	def create_grid_layout(self, nrows: int, ncols: int) -> Tuple["Figure", Sequence[Sequence["Axes"]]]:
		"""Create a subplot grid with the configured ``figsize``."""
		fig, axes = plt.subplots(nrows, ncols, figsize=self.figsize)
		return fig, axes

	@staticmethod
	def add_inset(
			main_ax: "Axes",
			*,
			left: float,
			bottom: float,
			width: float,
			height: float
	) -> "Axes":
		"""Create inset axes anchored to ``main_ax``."""
		return main_ax.inset_axes((left, bottom, width, height))

	@staticmethod
	def show_plot() -> None:
		"""Display the figure using tight layout adjustments."""
		plt.tight_layout()
		plt.show()

	def save_plot(self, filename: str, *, dpi: int = 300, fig_format: str = ".png") -> str:
		"""Persist the current figure to disk and return the resolved path."""
		if not filename.endswith(f".{fig_format}"):
			filename += f"{filename}.{fig_format}"
		self.fig.savefig(filename, dpi=dpi, format=fig_format, bbox_inches='tight')
		LOG.info("Saved figure with plot to %s", filename)
		return filename
