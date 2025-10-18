# src/sciwork/fs/select.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union, List, Tuple, Literal

from ..logutil import get_logger
from .base import PathLike, PathOpsBase
from .select_utils import (
	norm_exts, maybe_rel_one, maybe_rel_list,
	parse_index_list, normalize_indices,
	sort_fast, sort_with_meta
)

LOG = get_logger(__name__)

try:
	from .getcontents import GetContents
except ImportError:
	LOG.error("'sciwork.fs.select.Select' class requires the optional dependency 'sciwork.fs.getcontents.GetContents' to work.")
	raise

try:
	from ..console.prompter import Prompter
	prompter = Prompter()
except Exception:
	LOG.info("'sciwork.console.prompter.Prompter' not imported. The console output experience will be diminished.")
	prompter = None

__all__ = ["Select"]


class Select(PathOpsBase):
	"""
	High-level selector built on top of class:`PathOpsBase`.

	Reuses a listing/filtering pipeline (``get_files_and_folders`` and
	``get_contents``) and adds sorting and single/multiple selection.
	Programmatic via indices or interactive via :class:`sciwork.console.Prompter`.
	"""
	# --- Helpers: collect ---
	@staticmethod
	def _collect_fast(
			root: Path,
			*,
			recursive: bool,
			include_hidden: bool,
			follow_symlinks: bool,
			pattern: Optional[str],
			antipattern: Optional[str],
			shell_pattern: Optional[str],
			path_type: str,
			allowed_exts: Optional[Iterable[str]],
	) -> List[Path]:
		"""Collect only paths (no metadata) via :meth:`get_files_and_folders`."""
		ff_dict = GetContents().get_files_and_folders(
			root,
			recursive=recursive,
			include_hidden=include_hidden,
			follow_symlinks=follow_symlinks,
			pattern=pattern,
			antipattern=antipattern,
			shell_pattern=shell_pattern,
			return_absolute_paths=True
		)
		files, folders = ff_dict["files"], ff_dict["folders"]
		if allowed_exts:
			norms = norm_exts(allowed_exts)
			files = [p for p in files if p.suffix.lower() in norms]

		out = files if path_type == "files" else folders if path_type == "folders" else (files + folders)
		return [p if isinstance(p, Path) else Path(p) for p in out]

	@staticmethod
	def _collect_with_meta(
			root: Path,
			*,
			recursive: bool,
			include_hidden: bool,
			follow_symlinks: bool,
			pattern: Optional[str],
			antipattern: Optional[str],
			shell_pattern: Optional[str],
			path_type: str,
			allowed_exts: Optional[Iterable[str]],
	) -> List[Tuple[Path, dict]]:
		"""
		Collect (path, metadata) pairs via :meth:`get_contents` and filter by
		type/extensions.
		"""
		listing = GetContents().get_contents(
			root,
			recursive=recursive,
			include_hidden=include_hidden,
			follow_symlinks=follow_symlinks,
			pattern=pattern,
			antipattern=antipattern,
			shell_pattern=shell_pattern,
			exif=False,
			max_items=None,
			ignore_errors=True,
			return_absolute_paths=True
		)
		if not listing:
			return []

		norms = norm_exts(allowed_exts or [])
		items: List[Tuple[Path, dict]] = []
		for p_str, meta in listing.items():
			p = Path(p_str)
			kind = meta.get("type")
			if path_type == "files" and kind != "file":
				continue
			if path_type == "folders" and kind != "dir":
				continue
			if allowed_exts and kind == "file" and p.suffix.lower() not in norms:
				continue
			items.append((p, meta))
		return items

	# --- Helpers: select ---
	@staticmethod
	def _prompt_texts(root: Path, candidates: list[Path], selection_type: Literal["one", "many"]) -> Tuple[list[str], str]:
		"""Build a list of lines and a hint for the prompt."""
		instruction = "Please select one" if selection_type == "one" else "Please select many"
		prompt_c = prompter.palette.get("prompt", "") if prompter else ""
		reset_c = prompter.palette.get("reset", "") if prompter else ""
		hint_c = prompter.palette.get("hint", "") if prompter else ""

		lines = [f"{prompt_c}\nMultiple entries found in '{root}'. {instruction}:{reset_c}\n"]
		width = len(str(len(candidates)))
		for i, p in enumerate(candidates, 1):
			suffix = " (dir)" if p.is_dir() else ""
			lines.append(f"{i:>{width}}: {p.name}{suffix}")
		lines.append("")
		hint = (f"Enter a number {hint_c}[1...{len(candidates)}]" if selection_type == "one"
		        else f"Enter indices {hint_c}(comma/range, e.g. 1,3,5-7) within 1..{len(candidates)}")
		return lines, hint

	def _select_one(
			self,
			candidates: List[Path],
			*,
			root: Path,
			default_index: Optional[int],
			prompt_text: Optional[str]
	) -> Path:
		"""Pick a single path from the candidates (index or interactive)."""
		if len(candidates) == 1 and default_index is None:
			LOG.info("Single candidate in '%s': %s", root, candidates[0])
			return candidates[0].resolve()

		if default_index is not None:
			if not (1 <= default_index <= len(candidates)):
				raise ValueError(f"default_index out of range (1..{len(candidates)}), got {default_index}")
			sel = candidates[default_index - 1]
			LOG.info("Selected by default_index %d: %s", default_index, sel)
			return sel.resolve()

		lines, hint = self._prompt_texts(root, candidates, "one")
		prompter.print_lines(lines)
		ptxt = prompt_text or hint

		def _validate_num(s: str):
			number = int(s)
			if not (1 <= number <= len(candidates)):
				raise ValueError(f"Enter 1...{len(candidates)}")

		if prompter is not None:
			n = prompter.prompt(ptxt, validate=_validate_num, allow_empty=False, retries=3)
		else:
			n = input(ptxt)

		sel = candidates[int(n) - 1]
		LOG.info("Selected by prompt: %s", sel)
		return sel.resolve()

	def _select_many(
			self,
			candidates: List[Path],
			*,
			root: Path,
			default_indices: Optional[Iterable[int]],
			prompt_text: Optional[str]
	) -> List[Path]:
		"""
		Pick multiple paths.

		Accepts comma-separated indices and ranges in the prompt, e.g.:
		``1,3,5-7``. Indices are 1-based.
		"""
		if default_indices:
			indices = normalize_indices(default_indices, len(candidates))
			selected = [candidates[i - 1].resolve() for i in indices]
			LOG.info("Selected by default_indices %s (%d items)", list(indices), len(selected))
			return selected

		lines, hint = self._prompt_texts(root, candidates, "many")

		if prompter is not None:
			prompter.print_lines(lines)
		else:
			print([f"{line}\n" for line in lines])

		ptxt = prompt_text or hint

		def _transform_list(s: str):
			return parse_index_list(s, len(candidates))

		def _validate_list(lst: list[int]):
			if not lst:
				raise ValueError("No indices selected")
			n = len(candidates)
			if any((i < 1 or i > n) for i in lst):
				raise ValueError(f"Enter indices within 1...{n}.")

		if prompter is not None:
			indices: list[int] = prompter.prompt(
				ptxt,
				transform=_transform_list,
				validate=_validate_list,
				allow_empty=False,
				retries=3
			)
		else:
			indices = [int(i) for i in input(ptxt).split(",")]

		selected = [candidates[int(i) - 1].resolve() for i in indices]
		LOG.info("Selected by prompt %s (%d items)", indices, len(selected))
		return selected

	# --- public API ---
	def select_paths(
			self,
			folder_path: Optional[PathLike] = None,
			*,
			recursive: bool = False,
			include_hidden: bool = True,
			follow_symlinks: bool = False,
			pattern: Optional[str] = None,
			antipattern: Optional[str] = None,
			shell_pattern: Optional[str] = None,
			sort_by: Literal['name', 'ctime', 'mtime', 'size', 'ext', 'exts'] = "name",
			path_type: Literal['files', 'folders', 'any'] = "files",
			allowed_exts: Optional[Iterable[str]] = None,
			descending: bool = False,
			multiple: bool = False,  # allow selecting multiple entries
			default_index: Optional[int] = None,  # single selection (1-based)
			default_indices: Optional[Iterable[int]] = None,  # multiple selection (1-based)
			prompt_text: Optional[str] = None,
			return_absolute_paths: bool = False
	) -> Union[Path, List[Path]]:
		"""
		Selector one or many paths from a folder using the existing listing/filtering pipeline.

		Strategy
		--------
		* If sorting is ``name``/``ext`` only → use a fast path via
		  :meth:`get_files_and_folders`.
		* If sorting is ``ctime``/``mtime``/``size`` → use :meth:`get_contents`.
		  (needs metadata)
		* A single candidate returns immediately; otherwise select by index/indices, or
		  interactively via :class:`sciwork.console.Prompter`.

		:param folder_path: Root directory (absolute or relative to ``base_dir``).
							If ``None``, `folder_path` defaults to ``self.base_dir``.
		:param recursive: Recurse into subdirectories.
		:param include_hidden: Include dot-entries.
		:param follow_symlinks: Follow directory symlinks during recursion.
		:param pattern: Text pattern to be included in the file names.
		:param antipattern: Text pattern to be excluded from the file names.
		:param shell_pattern: Shell-like pattern to be included in the file names.
		:param sort_by: ``'name'`` (default), ``'ctime'``, ``'mtime'``, ``'size'``, ``'ext'``, (``'exts'`` is an alias).
		:param path_type: ``'files'`` (default), ``'folders'``, ``'any'``.
		:param allowed_exts: Allowed extensions for files (e.g., ``['.csv', '.jpg']``).
		:param descending: Sort descending.
		:param multiple: If ``True``, allow selecting **multiple** entries (returns a list).
		:param default_index: Single selection (1-based). If set, bypasses the prompt.
		:param default_indices: Multiple selection (1-based). If set, bypasses the prompt.
		:param prompt_text: Custom prompt text (when prompting is needed).
		:param return_absolute_paths: If ``False``, results are returned relative to the chosen root.
		:return: Either a single selected path (``multiple=False``), or a list of paths (``multiple=True``).
		:raises FileNotFoundError: When no matching entries are found.
		:raises ValueError: On invalid parameters, selection or index is out of range.
		"""
		try:
			from .dirs import Dirs
		except ImportError:
			LOG.error("'Select.select_paths' method requires the optional dependency 'sciwork.fs.dirs.Dirs' to work.")
			raise

		root = Dirs().try_get_dir(folder_path) if folder_path else self.base_dir

		sort_norm = sort_by.lower()
		if sort_norm == "exts":
			sort_norm = "ext"
		if path_type not in {"files", "folders", "any"}:
			raise ValueError(f"path_type must be one of: 'files', 'folders', 'any': {path_type}")
		need_meta = sort_norm in {"ctime", "mtime", "size"}

		# 1) Collect candidates
		if need_meta:
			candidates = self._collect_with_meta(
				root,
				recursive=recursive,
				include_hidden=include_hidden,
				follow_symlinks=follow_symlinks,
				pattern=pattern,
				antipattern=antipattern,
				shell_pattern=shell_pattern,
				path_type=path_type,
				allowed_exts=allowed_exts
			)
			candidates = sort_with_meta(candidates, sort_norm, descending)
			cand_paths = [p for p, _ in candidates]
		else:
			cand_paths = self._collect_fast(
				root,
				recursive=recursive,
				include_hidden=include_hidden,
				follow_symlinks=follow_symlinks,
				pattern=pattern,
				antipattern=antipattern,
				shell_pattern=shell_pattern,
				path_type=path_type,
				allowed_exts=allowed_exts
			)
			cand_paths = sort_fast(cand_paths, sort_norm, descending)

		if not cand_paths:
			raise FileNotFoundError(f"No matching entries found in '{root}'")

		# 2) Selection
		if multiple:
			selected = self._select_many(
				cand_paths,
				root=root,
				default_indices=default_indices,
				prompt_text=prompt_text
			)
			return maybe_rel_list(selected, root, return_absolute_paths)

		# single selection
		chosen = self._select_one(
			cand_paths,
			root=root,
			default_index=default_index,
			prompt_text=prompt_text
		)
		return maybe_rel_one(chosen, root, return_absolute_paths)
