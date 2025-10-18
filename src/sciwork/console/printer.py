# src/sciwork/console/printer.py

from __future__ import annotations

import sys
from typing import Any, Optional, Protocol, Literal
from collections.abc import Mapping as _Mapping, Iterable as _Iterable

from ..logutil import get_logger
from .bootstrap import ensure_ansi_colors
from ..config import RobustConfig

LOG = get_logger(__name__)


class _Writable(Protocol):
	def write(self, __s: str) -> object: ...

	def isatty(self) -> bool: ...


class Printer:
	"""
    Color-aware, nest-friendly pretty printer for Python structures.

    Features
    --------
    - Dicts: inline scalars (``key: value``), nested values expand with indentation.
    - Lists/Tuples/Sets: index/marker labels, nested values expand.
    - Optional ANSI color (auto disabled when the stream is not a TTY).
    - Optional type hints (``(str)``, ``(int)``, ...).
    - String truncation for long values.

    Notes
    -----
    The color palette is loaded from ``ansi_colors.json`` which is ensured on first
    use via :func:`sciwork.console.create_ansi_colors_config`. The default location is
    ``<cwd>/sciwork/configs/ansi_colors.json``; switch to the user location by
    calling :class:`Printer` with ``prefer='user'``.
    """

	def __init__(
			self,
			*,
			prefer: Literal['project', 'user'] = "project",
			use_color: bool = True,
			indent_unit: int = 4
	) -> None:
		self._indent_unit = int(indent_unit)
		self._use_color_flag = bool(use_color)
		self._ctx_stack: list[dict[str, object]] = []

		theme_path = ensure_ansi_colors(prefer=prefer)
		palette_theme = RobustConfig().load_json_config(theme_path).to_dict()
		self.palette = self._load_palette(palette_theme)

	def __repr__(self) -> str:
		"""Unambiguous representation of printer."""
		return (f"{self.__class__.__name__}("
		        f"use_color={self._use_color_flag}, "
		        f"palette_keys={list(self.palette.keys())}")

	def __str__(self) -> str:
		"""Concise representation of printer."""
		state = "on" if self._use_color_flag else "off"
		return f"{self.__class__.__name__} (color={state})"

	def __enter__(self):
		"""
        Enter context.

        Saves actual "user-adjustable" states so that they are renewed by __exit__.
        Attributes are changeable within the block:
            with printer as p:
                p._use_color_flag = False
                p.printer(obj)
        """
		self._ctx_stack.append({
			"use_color": getattr(self, "_use_color_flag", True),
			"palette": getattr(self, "palette", {}),
		})
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
		"""
        Exit context: renews the state before entering the block.
        :return: False.
        """
		state = self._ctx_stack.pop() if self._ctx_stack else None
		if state:
			try:
				self._use_color_flag = state["use_color"]  # type: ignore[assignment]
				self.palette = state["palette"]  # type: ignore[assignment]
			except Exception:
				pass
		return False

	def _load_palette(self, palette_theme: dict[str, dict[str, Any]]) -> dict[str, str]:
		"""
        Build the in-memory color palette from the theme dict.
        Falls back to safe defaults when keys are missing.

        :param palette_theme: Theme dict (loaded from ``ansi_colors.json``).
        :return: Palette dictionary with object name as keys and color codes as values.
        """
		style = palette_theme.get("style", {})
		bfg = palette_theme.get("bfg", {})

		# Safe defaults
		reset = style.get("RESET", "\u001b[0m")
		green = bfg.get("GREEN", "\u001b[92m")
		cyan = bfg.get("CYAN", "\u001b[96m")
		blue = bfg.get("BLUE", "\u001b[94m")
		red = bfg.get("RED", "\u001b[91m")
		white = bfg.get("WHITE", "\u001b[97m")
		yellow = bfg.get("YELLOW", "\u001b[93m")
		magenta = bfg.get("MAGENTA", "\u001b[95m")
		black = bfg.get("BLACK", "\u001b[90m")

		self.palette = {
			"key": green,
			"list": cyan,
			"tuple": red,
			"set": white,
			"scalar": reset,
			"type": blue,
			"reset": reset,
			"rule": blue,
			"dots": red,
			"green": green,
			"cyan": cyan,
			"blue": blue,
			"red": red,
			"white": white,
			"yellow": yellow,
			"magenta": magenta,
			"black": black,
		}

		return self.palette

	# --- small helpers ---
	@staticmethod
	def _is_scalar(x: Any) -> bool:
		"""
        Decide if an object is a scalar value (printed directly).

        Scalars are str, bytes, int, float, bool, or None.
        Everything else is considered a container.

        :param x: Object to test.
        :return: True if scalar, False otherwise.
        """
		return isinstance(x, (str, bytes, int, float, bool, type(None)))

	def _pad(self, indent: int) -> str:
		"""
        Return spaces for the given indent level.

        :param indent: Current indent level.
        :return: The actual indent.
        """
		return " " * (indent * self._indent_unit)

	@staticmethod
	def _type_tag(x: Any, show_types: bool) -> str:
		"""
        Create a string with the object's type in parentheses.
        Used when 'show_types=True'.

        :param x: Object whose type is shown.
        :param show_types: Flag controlling type output.
        :return: String like "(str)" or "" if 'show_types=False'.
        """
		return f" ({type(x).__name__})" if show_types else ""

	@staticmethod
	def _truncate(s: str, max_str: Optional[int]) -> str:
		"""
        Truncate long strings to a maximum length with an ellipsis.

        :param s: Input string.
        :param max_str: Maximum length before truncation.
        :return: Truncated string with "..." if longer than 'max_str'.
        """
		if max_str is not None and isinstance(s, str) and len(s) > max_str:
			return s[: max(0, max_str - 1)] + "..."
		return s

	@staticmethod
	def _supports_color(stream: _Writable, use_color: bool) -> bool:
		"""
        Determine whether ANSI colors should be enabled.
        Colors are enabled only if:
         - the 'use_color' flag is True, and
         - the output stream is a TTY or colorama is available.

        :param stream: Output stream (e.g., sys.stdout).
        :param use_color: Boolean flag to allow/disallow colors.
        :return: True if colors are supported, False otherwise.
        """
		try:
			return use_color and hasattr(stream, "isatty") and stream.isatty()
		except Exception:
			return False

	@staticmethod
	def _normalize_iterable(obj: _Iterable) -> tuple[list[Any], bool, bool]:
		"""
        Normalize an arbitrary iterable into a list and identify its container kind.

        For sets the function attempts to produce a *stable* order (sorted by ``str(x)``),
        falling back to an arbitrary list order if sorting fails. Tuples are reported via
        the ``is_tuple`` flag, so the caller may render different index labels.

        :param obj: Iterable object to normalize (strings and mappings are handled elsewhere).
        :return: A triple ``(items, is_set, is_tuple)``.
        """
		is_set = isinstance(obj, set)
		is_tuple = isinstance(obj, tuple)
		if is_set:
			try:
				return sorted(obj, key=lambda x: str(x)), True, is_tuple
			except Exception:
				return list(obj), True, is_tuple
		if isinstance(obj, (list, tuple)):
			return list(obj), False, is_tuple
		# Generic iterables (avoid strings/dicts which are handled elsewhere)
		try:
			return list(obj), False, is_tuple
		except Exception:
			return [obj], False, is_tuple

	def _label_for(self, idx: int, is_tuple: bool, is_set: bool) -> str:
		"""
        Build a label for tuple and set iterable items.

        :param idx: Index of item.
        :param is_tuple: True, if the item is a tuple.
        :param is_set: True, if the item is a set.
        :return: Index label to be printed.
        """
		if is_tuple:
			return f"{self.palette['tuple']}({idx}){self.palette['reset']}"
		if is_set:
			return f"{self.palette['set']}{{•}}{self.palette['reset']}"
		return f"{self.palette['list']}[{idx}]{self.palette['reset']}"

	# --- helpers: printers per kind ---
	def _print_scalar(
			self,
			obj: Any,
			*,
			pad: str,
			max_str: Optional[int],
			show_types: bool,
			stream: _Writable
	) -> None:
		"""
        Print a scalar value (str, bytes, int, float, bool, None) on a single line.

        :param obj: Scalar value to print.
        :param pad: Left padding (spaces) derived from the current indent.
        :param max_str: Max length for strings; longer strings are truncated with an ellipsis.
        :param show_types: Whether to append a dimmed type tag like "(str)".
        :param stream: Output stream to write to.
        """
		val = self._truncate(obj, max_str) if isinstance(obj, str) else obj
		type_str = f"{self.palette['type']}{self._type_tag(obj, show_types)}{self.palette['reset']}"
		print(f"{pad}{self.palette['scalar']}{val}{self.palette['reset']}{type_str}", file=stream)

	def _print_mapping(
			self,
			mapping: _Mapping,
			*,
			indent: int,
			sort_keys: bool,
			show_types: bool,
			max_str: Optional[int],
			stream: _Writable
	) -> None:
		"""
        Print a mapping (dict-like). Scalar values are printed inline as 'key: value'.
        Nested containers are printed on the next line with increased indentation.

        :param mapping: The dictionary-like object to print.
        :param indent: Current indentation level.
        :param sort_keys: Sort keys alphabetically (safe only if keys are comparable).
        :param show_types: Whether to append a dimmed type tak for values.
        :param max_str: Max length for strings; longer strings are truncated.
        :param stream: Output stream to write to.
        """
		items = mapping.items()
		if sort_keys:
			try:
				items = sorted(items, key=lambda kv: str(kv[0]))
			except Exception:
				# Keep original order when keys are not comparable
				pass

		pad = self._pad(indent)
		for k, v in items:
			key_str = f"{self.palette['key']}{k}{self.palette['reset']}"
			if self._is_scalar(v):
				sval = self._truncate(v, max_str) if isinstance(v, str) else v
				type_str = f"{self.palette['type']}{self._type_tag(v, show_types)}{self.palette['reset']}"
				print(f"{pad}{key_str}: {self.palette['scalar']}{sval}{self.palette['reset']}{type_str}", file=stream)
			else:
				print(f"{pad}{key_str}:", file=stream)
				self.printer(
					v,
					indent=indent + 1,
					sort_keys=sort_keys,
					show_types=show_types,
					max_str=max_str,
					stream=stream
				)

	def _print_iterable(
			self,
			iterable: _Iterable,
			*,
			indent: int,
			show_types: bool,
			max_str: Optional[int],
			stream: _Writable
	) -> None:
		"""
        Print iterable (list/tuple/set/another sequence). Scalar items are printed inline
        with an index/label on the same line; nested containers expand with indentation.

        :param iterable: The iterable to print (must not be a string/bytes/dict).
        :param indent: Current indentation level.
        :param show_types: Whether to append a dimmed type tag for values.
        :param max_str: Max length for strings; longer strings are truncated.
        :param stream: Output stream to write to.
        """
		norm, is_set, is_tuple = self._normalize_iterable(iterable)
		pad = self._pad(indent)

		for idx, item in enumerate(norm):
			label = self._label_for(idx, is_tuple, is_set)
			label_col = f"{label}{self.palette['reset']}"

			if self._is_scalar(item):
				sval = self._truncate(item, max_str) if isinstance(item, str) else item
				type_str = f"{self.palette['type']}{self._type_tag(item, show_types)}{self.palette['reset']}"
				print(f"{pad}{label_col}: {self.palette['scalar']}{sval}{self.palette['reset']}{type_str}", file=stream)
			else:
				print(f"{pad}{label_col}:", file=stream)
				self.printer(
					item,
					indent=indent + 1,
					sort_keys=True,  # sorting only applies to dicts deeper down
					show_types=show_types,
					max_str=max_str,
					stream=stream
				)

	# ----------------- public API -------------------
	def printer(
			self,
			obj: Any,
			indent: int = 0,
			sort_keys: bool = True,
			show_types: bool = False,
			max_str: Optional[int] = 200,
			stream: _Writable = sys.stdout
	) -> None:
		"""
        Pretty-prints nested Python structures (dict, list, tuple, set, etc.) with inline
        keys/indices on the same line. Supports optional color, type hints, sorting of dict keys,
        and string truncation for readability.

        Behavior
        --------
        * Dicts: 'key: value' on a single line when value is scalar; nested values expand with indentation.
        * Lists: '[idx]: value' on a single line when scalar; nested values expand.
        * Tuples: '(idx): value' labels.
        * Sets: '{•}: value' labels (order not guaranteed; sorted when possible).
        * Scalars: printed directly; long strings are truncated to 'max_str' characters.

        :param obj: Object to be printed.
        :param indent: Current indentation level (internal for recursion).
        :param sort_keys: Sort dictionary keys alphabetically (safe if keys are comparable).
        :param show_types: Append the value's type in a dim style, e.g., '(str)'.
        :param max_str: Truncate strings longer than this length with an ellipsis.
        :param stream: Output stream; defaults to sys.stdout.

        Notes
        -----
        * Colors automatically fall back to plain text if ANSI is not supported.
        * Errors are logged using 'logging.error(..., exc_info=True)'.
        """
		enable_color = self._supports_color(stream, self._use_color_flag)
		orig_palette = self.palette
		try:
			if not enable_color:
				self.palette = {k: "" for k in orig_palette}

			# Mapping
			if isinstance(obj, _Mapping):
				self._print_mapping(
					obj, indent=indent, sort_keys=sort_keys, show_types=show_types,
					max_str=max_str, stream=stream
				)
				return

			# Iterable
			if isinstance(obj, _Iterable) and not isinstance(obj, (str, bytes, dict)):
				self._print_iterable(
					obj, indent=indent, show_types=show_types,
					max_str=max_str, stream=stream
				)
				return

			# Scalar
			self._print_scalar(
				obj, pad=self._pad(indent), max_str=max_str, show_types=show_types,
				stream=stream
			)

		except Exception as e:
			LOG.error(f"Error while printing object: {e}", exc_info=True)
			raise
		finally:
			self.palette = orig_palette
