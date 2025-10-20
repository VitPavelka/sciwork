# src/sciwork/plot/plot.py

from __future__ import annotations

from .decor import Decor
from .drawing import Drawing
from .layout import Layout
from .ticks import Ticks


class Plot(Decor, Drawing, Layout, Ticks):
	"""Featureful Matplotlib figure manager with SciWork integrations."""

	__slots__ = ()
