from __future__ import annotations

import shutil
import sys
from typing import Optional, Protocol, runtime_checkable, TextIO


@runtime_checkable
class _SupportsWrite(Protocol):
	def write(self, __s: str) -> object: ...


@runtime_checkable
class _SupportsWriteAndFlush(_SupportsWrite, Protocol):
	def flush(self) -> object: ...


_Stream = _SupportsWriteAndFlush | TextIO


def format_interval(start_time: float, end_time: float, *, ms: bool = False) -> str:
	"""
	Format the elapsed time between two timestamps into a readable string.

	:param start_time: Start time in seconds (e.g., from ``time.perf_counter()``).
	:param end_time: End time in seconds.
	:param ms: When ``True``, append milliseconds as well.
	:return: Human-friendly time span, e.g. ``"1 h 02 min 03 s"`` or
			``"45 s 120 ms"`` when ``ms=True``.
	"""
	interval = max(0.0, end_time - start_time)

	whole_seconds = int(interval)
	milliseconds = int(round((interval - whole_seconds) * 1000))

	hours, rem = divmod(whole_seconds, 3600)
	minutes, seconds = divmod(rem, 60)

	parts: list[str] = []
	if hours > 0:
		parts.append(f"{int(hours)} h")
	if minutes > 0:
		parts.append(f"{int(minutes)} min")
	if seconds > 0 or not parts:
		parts.append(f"{int(seconds)} s")
	if ms:
		parts.append(f"{milliseconds} ms")
	return " ".join(parts)


def print_rule(
		times: int = 1,
		*,
		prespace: bool = True,
		char: str = "-",
		width: Optional[int] = None,
		stream: _Stream = sys.stdout,
		prefix: str = "",
		suffix: str = ""
) -> int:
	"""
	Print a horizontal rule (optionally multiple times).

	:param times: How many lines to print. Defaults to 1.
	:param prespace: Print a blank line before the rules. Defaults to ``True``.
	:param char: Single character used to build the rule. Defaults to ``"-"``.
	:param width: Target width. If omitted, the terminal width is detected (fallback 100).
	:param stream: Destination stream; defaults to ``sys.stdout``.
	:param prefix: Optional string printed before the rule (e.g., ANSI color).
	:param suffix: Optional string printed after the rule (e.g., reset color).
	:return: The width that was used for the rule.
	"""
	if prespace:
		print("", file=stream)

	if not width:
		width = shutil.get_terminal_size(fallback=(100, 24)).columns
		width = max(20, width)

	line = char * width
	for _ in range(max(1, times)):
		print(f"{prefix}{line}{suffix}", file=stream)
	return width


def next_dots(
		current_count: int,
		*,
		max_dots: int = 5,
		stream: _Stream = sys.stdout,
		prefix: str = "",
		suffix: str = ""
) -> int:
	"""
	Print a simple dot-loading animation step and return the updated count.

	The function prints one dot each call until ``max_dots`` is reached, then
	clears the line segment and starts over.

	``prefix`` and ``suffix`` are optional strings that are printed before and after
	and are visually static.

	:param current_count: Current number of dots *already* printed in the active cycle.
	:param max_dots: Maximum dots before resetting. Defaults to 5.
	:param stream: Destination stream; defaults to ``sys.stdout``.
	:param prefix: Optional text/ANSI printed before the dots.
	:param suffix: Optional text/ANSI printed after the dots.
	:return: Updated dot counter to be fed back into the next call.
	"""
	n = max(0, min(current_count, max_dots - 1))
	dots = "." * (n + 1)
	pad = " " * (max_dots - (n + 1))
	print(f"\r{prefix}{dots}{pad}{suffix}", end="", flush=True, file=stream)
	return 0 if n + 1 >= max_dots else (n + 1)
