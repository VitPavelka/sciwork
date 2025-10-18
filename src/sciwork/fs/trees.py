# src/sciwork/fs/trees.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .base import PathOpsBase
from ..logutil import get_logger
from .trees_utils import build_branch, looks_like_file

LOG = get_logger(__name__)

try:
	from .create import Create
except ImportError:
	LOG.error("'sciwork.fs.trees.TreeOps' class requires the optional dependency 'sciwork.fs.create.Create' to work.")
	raise


class TreeOps(PathOpsBase):
	"""Filesystem tree builder."""
	def build_tree(
			self,
			tree_dict: Dict[str, List[str]],
			*,
			file_mode: str = "a"
	) -> Dict[str, Path]:
		"""
		Create a filesystem tree based on an adjacency dictionary.

		**Input shape**
			- ``tree_dict["parents"]``: list of root components (strings)
			- For each internal node: ``parent_name: [child1, child2, ...]``
			- Each *leaf* is the last component of the branch. If it looks like a file
				(it has known suffix), creates an empty file, otherwise creates a directory.

		Example::
			{
				"parents": ["data"],
				"data": ["raw", "processed"],
				"raw": ["in.csv", "out.txt"],
				"processed": ["table.xlsx"]
			}

		:param tree_dict: Adjacency mapping with a required 'parents' key.
		:param file_mode: Mode passed to :meth:`create_file` for leaf files ('a'|'w'|'x').
		:return: Mapping leaf name -> absolute Path created (dir or file).
		:raises KeyError: If 'parents' key is missing.
		:raises ValueError: On invalid topology (cycles, multiple parents, orphan nodes).
		"""
		if "parents" not in tree_dict:
			raise KeyError("tree_dict must contain a 'parents' key with root nodes.")
		roots = list(tree_dict["parents"])
		if not isinstance(roots, list) or not roots:
			raise ValueError("'parents' must be a non-empty list of root components.")

		# Determine leaves: children that never appear as keys (i.e., not parents)
		all_children = {c for k, vals in tree_dict.items() if k != "parents" for c in vals}
		leaves = sorted(all_children - set(tree_dict.keys()))  # children that are not parents themselves

		created: Dict[str, Path] = {}
		for leaf in leaves:
			components = build_branch(leaf, tree_dict, roots)
			target = self.base_dir.joinpath(*components)

			if looks_like_file(leaf):
				# ensure parent and create a file
				Create().create_file(target, op=file_mode, create_parents=True)
				kind = "file"
			else:
				Create().make_folder(target, exist_ok=True)
				kind = "folder"

			abs_path = target.resolve()
			created[leaf] = abs_path
			LOG.info("Created %s: %s", kind, abs_path)

		return created
