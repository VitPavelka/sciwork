# src/sciwork/console/console.py

from __future__ import annotations

import sys
from typing import Optional, TextIO

from .base import format_interval, print_rule as _print_rule_plain, next_dots as _next_dots_plain
from .prompter import Prompter


class Console(Prompter):
	"""
	High-level console helper that extends :class:`Printer` with convenience methods
	for timing, rules (horizontal lines), and a simple dot-loading animation.

	Color Usage
	-----------
	The class reuses the :class:`Printer` palette and will look up optional roles:

	-``"rule"``: color for horizontal rules
	- ``"dots"``: color for the dot animation

	If a role is not present in the palette, it falls back to a neutral style.
	"""
	# --- timing ---
	@staticmethod
	def time_count(start_time: float, end_time: float, *, ms: bool = False) -> str:
		"""
		Format the elapsed time between two timestamps into a readable string.

		:param start_time: Start time in seconds (e.g., from ``time.perf_counter()``).
		:param end_time: End time in seconds.
		:param ms: When ``True``, append milliseconds as well.
		:return: Human-friendly time span, e.g. ``"1 h 02 min 03 s"`` or
				``"45 s 120 ms"`` when ``ms=True``.
		"""
		return format_interval(start_time, end_time, ms=ms)

	# --- rules (horizontal lines) ---
	def rule(
			self,
			times: int = 1,
			*,
			prespace: bool = True,
			char: str = "-",
			width: Optional[int] = None,
			stream: TextIO = sys.stdout,
			color_role: str = "rule"
	) -> int:
		"""
		Print a colored horizontal rule (optionally multiple times).

		:param times: How many lines to print. Defaults to 1.
		:param prespace: Print a blank line before the rules. Defaults to ``True``.
		:param char: Single character used to build the rule. Defaults to ``"-"``.
		:param width: Target width. If omitted, the terminal width is detected (fallback 100).
		:param stream: Output stream; defaults to ``sys.stdout``.
		:param color_role: Palette role to colorize the rule. Defaults to ``"rule"``.
		:return: The width that was used for the rule.
		"""
		use_color = self._supports_color(stream, self._use_color_flag)
		color = self.palette.get(color_role, "") if use_color else ""
		reset = self.palette.get("reset", "") if use_color else ""
		return _print_rule_plain(
			times=times,
			prespace=prespace,
			char=char,
			width=width,
			stream=stream,
			prefix=color,
			suffix=reset
		)

	# --- dot animation ---
	def dot_loading_animation(
			self,
			current_count: int,
			*,
			max_dots: int = 5,
			stream: TextIO = sys.stdout,
			color_role: str = "dots",
			left: str = "",
			right: str = ""
	) -> int:
		"""
		Print one step of a dot-loading animation and return the updated count.
		Dots are colorized using a palette role (if color is supported).

		:param current_count: Current number of dots already printed in the active cycle.
		:param max_dots: Maximum dots before resetting. Defaults to 5.
		:param stream: Output stream; defaults to ``sys.stdout``.
		:param color_role: Palette role to colorize the dots. Defaults to ``"dots"``.
		:param left: Static text printed to the left of the dots.
		:param right: Static text printed to the right of the dots.
		:return: Updated dot counter to be fed back into the next call.
		"""
		use_color = self._supports_color(stream, self._use_color_flag)
		color = self.palette.get(color_role, "") if use_color else ""
		reset = self.palette.get("reset", "") if use_color else ""

		prefix = f"{color}{left}"
		suffix = f"{right}{reset}"

		return _next_dots_plain(
			current_count=current_count,
			max_dots=max_dots,
			stream=stream,
			prefix=prefix,
			suffix=suffix
		)
