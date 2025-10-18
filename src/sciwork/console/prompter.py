# src/sciwork/console/prompter.py

from __future__ import annotations

import sys
from typing import Callable, Optional, Sequence, TextIO, Protocol, runtime_checkable, Iterable, Any, TypeVar, Union

from .printer import Printer, _Writable
from ..logutil import get_logger

LOG = get_logger(__name__)
_T = TypeVar("_T")


@runtime_checkable
class _SupportsWrite(Protocol):
	def write(self, __s: str) -> object: ...


@runtime_checkable
class _SupportsWriteAndFlush(_SupportsWrite, Protocol):
	def flush(self) -> object: ...


_Stream = _SupportsWriteAndFlush | TextIO


class Prompter(Printer):
	"""
	Mixin that adds colored prompting utilities to console classes.

	This mixin expects the subclass to expose:

	- ``self.palette``: ``dict[str, str]`` with ANSI escapes.
	- ``self._use_color_flag``: ``bool`` toggle for color usage.
	- ``self._supports_color(stream: TextIO, use_color_flag: bool) -> bool``

	Typically, :class:`~sciwork.console.printer.Printer` already provides these.
	"""
	def __init__(self, *, use_color: bool = True, stream: _Writable = sys.stdout, **kwargs) -> None:
		super().__init__(use_color=use_color, **kwargs)
		self.stream: _Writable = stream
		self._colors_enabled: bool = self._supports_color(self.stream, self._use_color_flag)
		self._ensure_prompt_palette()

	def _ensure_prompt_palette(self) -> None:
		"""Add prompt-specific semantic roles to the palette (non-destructively)."""
		pal = dict(self.palette or {})
		pal.setdefault("prompt", pal.get("green", ""))
		pal.setdefault("value", pal.get("reset", ""))
		pal.setdefault("hint", pal.get("blue", ""))
		pal.setdefault("error", pal.get("red", ""))
		pal.setdefault("reset", pal.get("reset", ""))
		self.palette = pal

	def print_lines(self, lines: Iterable[str], *, stream: _Writable = sys.stdout) -> None:
		"""
		Print a block of lines to the console, flushing after each line.
		Safer on Windows than passing a giant multi-line string into input().

		:param lines: Iterable of strings to print.
		:param stream: Output stream; defaults to sys.stdout.
		"""
		stream = stream or self.stream
		for line in lines:
			print(line, file=stream)

	# --- small helpers ---
	@staticmethod
	def _build_hint_suffix(
			*,
			default: Optional[str],
			choices: Optional[Sequence[str]],
			hint_color: str,
			reset: str
	) -> str:
		"""Build the colored suffix, e.g. ``[a|b|c] (default: x)``."""
		parts = []
		if choices:
			parts.append(f"{hint_color}[{'|'.join(map(str, choices))}]")
		if default is not None:
			parts.append(f"{hint_color}(default: {default})")
		return ((" ".join(parts)) + reset) if parts else ""

	@staticmethod
	def _normalize_retries(retries: int) -> int:
		"""Return a safe, positive number of attempts."""
		try:
			r = int(retries)
		except Exception:
			r = 3
		return max(1, r)

	@staticmethod
	def _readline(input_func: Callable[[str], str], prompt: str) -> str:
		"""Read one line of input and convert Ctrl-C into a user-friendly ValueError"""
		try:
			return input_func(prompt)
		except KeyboardInterrupt as exc:  # user hit ^C
			print()  # newline to move to the next line nicely
			raise ValueError("Prompt cancelled by user (Ctrl-C).") from exc

	@staticmethod
	def _apply_transform(value: str, transform: Optional[Callable[[str], Any]]) -> Any:
		"""Apply an optional transform and bubble up errors."""
		if transform is None:
			return value
		return transform(value)

	@staticmethod
	def _check_choices(value: Any, choices: Optional[Iterable[Any]]) -> None:
		"""Raise ValueError if *choices* parameter is provided and *value* is not a member."""
		if choices is not None and value not in choices:
			raise ValueError(f"Please choose one of: {', '.join(map(str, choices))}.")

	@staticmethod
	def _run_validator(value: Any, validate: Optional[Callable[[Any], None]]) -> None:
		"""Run optional validator which is expected to rise on invalid input."""
		if validate is not None:
			validate(value)

	# --- public API ---
	def prompt(
			self,
			message: str,
			*,
			default: Optional[str] = None,
			choices: Optional[Iterable[_T]] = None,
			validate: Optional[Callable[[_T], None]] = None,
			transform: Optional[Callable[[str], _T]] = None,
			allow_empty: bool = False,
			retries: int = 3,
			stream: _Stream = sys.stdout,
			input_func: Callable[[str], str] = input
	) -> Union[str, _T]:
		"""
		Prompt the user for a line of input with optional validation and coloring.

		The prompt can display a *default* value and a list of *choices*. It the user
		submits an empty line and *default* is provided, the default is returned.
		A *validate* callback may raise to reject the input; a *transform* callback
		may convert text (e.g. ``str.strip`` or ``str.lower``).

		:param message: Prompt message shown to the user (without trailing colon).
		:param default: Optional default value returned when the user presses Enter on an empty line.
		:param choices: Optional finite set of allowed values. If provided, input must be one of these.
		:param validate: Optional callable ``validate(value)`` that should raise on invalid input.
		:param transform: Optional callable ``transform(value) -> value`` to normalize the input.
		:param allow_empty: Allow returning an empty string when no default is set. Defaults to ``False``.
		:param retries: Number of attempts before raising ``ValueError``. Defaults to ``3``.
		:param stream: Output stream (colors are enabled only if TTY / color-capable).
		:param input_func: Input function to call (injectable for test).
		:return: Final (validated and transformed) value.
		:raises ValueError: If the user exceeds the allowed number of attempts or input is invalid.
		"""
		prompt_c = self.palette.get("prompt", "")
		hint_c = self.palette.get("hint", "")
		err_c = self.palette.get("error", "")
		reset = self.palette.get("reset", "")

		hint_suffix = self._build_hint_suffix(default=default, choices=choices, hint_color=hint_c, reset=reset)
		base = f"{prompt_c}{message}{reset}"
		full_prompt = (f"{base} {hint_suffix}" if hint_suffix else base) + ": "

		attempts = self._normalize_retries(retries)
		for _ in range(attempts):
			raw = self._readline(input_func, full_prompt)

			if raw == "":
				if default is not None:
					return default
				if allow_empty:
					return ""
				print(f"{err_c}Input cannot be empty.{reset}", file=stream, flush=True)
				continue

			try:
				value: Any = self._apply_transform(raw, transform)
				self._check_choices(value, choices)
				self._run_validator(value, validate)
				return value
			except Exception as exc:
				print(f"{err_c}{exc}{reset}", file=stream, flush=True)
		raise ValueError("Too many invalid attempts.")

	def confirm(
			self,
			message: str,
			*,
			default: bool = False,
			stream: _Stream = sys.stdout,
			input_func: Callable[[str], str] = input,
			yes_values: Sequence[str] = ("y", "yes"),
			no_values: Sequence[str] = ("n", "no"),
			transform: Callable[[str], str] = lambda s: s.strip().lower()
	) -> bool:
		"""
		Ask a yes/no question with a colored prompt and return a boolean.

		:param message: Question to show (e.g., ``"Proceed with deletion"``).
		:param default: Default answer when the user presses Enter.
						Controls the ``[Y/n]`` or ``[y/N]`` hint.
		:param stream: Output stream (colors are enabled only if TTY / color-capable).
		:param input_func: Input function to call (injectable for test).
		:param yes_values: Accepted case-insensitive strings for "yes".
		:param no_values: Accepted case-insensitive strings for "no".
		:param transform: Normalization function applied to raw input (default: lowercase and strip).
		:return: ``True`` for yes, ``False`` for no.
		"""
		allowed = tuple(x.lower() for x in (*yes_values, *no_values))
		y0 = next(iter(yes_values), "Y")
		n0 = next(iter(no_values), "N")
		yn_hint = "/".join([y0.upper() if default else y0, n0 if default else n0.upper()])

		ans = self.prompt(
			f"{message} {yn_hint}",
			default=("y" if default else "n"),
			choices=allowed,
			transform=transform,
			stream=stream,
			input_func=input_func
		)
		return ans in {v.lower() for v in yes_values}
