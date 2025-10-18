# src/sciwork/fs/trees_utils.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Dict, List


# --- Topology Helpers ---
def parent_map(tree: Mapping[str, List[str]], roots: Iterable[str]) -> Dict[str, str]:
	"""
	Build a child→parent map from an adjacency list and validate the shape.

	- `tree` is {parent: [children, ...], ...}. A special "parents" key (if present)
	   is ignored; roots are provided by `roots`.
	- validates duplicate parents and trivial self-cycles (child == parent).

	:param tree: Mapping parent -> list of children. Must contain the 'parents' key externally.
	:param roots: Iterable of rood node names.
	:return: Dict child -> parent.
	:raises ValueError: If a child has multiple parents or cycles likely exist.
	"""
	roots_set = set(roots)
	parent_of: Dict[str, str] = {}

	for parent, children in tree.items():
		if parent == "parents":
			continue
		if not isinstance(children, list):
			raise ValueError(f"Tree node '{parent}' must map to a list of children.")
		for child in children:
			if child in roots_set:
				# root cannot be a child at the same time
				raise ValueError(f"Node '{child}' is declared as root and as a child at the same time.")
			if child in parent_of and parent_of[child] != parent:
				raise ValueError(f"Node '{child}' has multiple parents: {parent_of[child]} and {parent}")
			parent_of[child] = parent

	for child, parent in parent_of.items():
		if child == parent:
			raise ValueError(f"Cycle detected: node '{child}' is its own parent.")

	return parent_of


def build_branch(
		leaf: str,
		tree_dict: Mapping[str, list[str]],
		parents_set: Iterable[str]
) -> list[str]:
	"""
	Build the path (root → ... → leaf) for a given *leaf* using a tree adjacency.

	The tree is represented as ``{parent: [children, ...], ...}`` and the special
	key ``"parents"`` (or externally added *parents_set*) contains the roots.

	:param leaf: Terminal node to resolve.
	:param tree_dict: Adjacency mapping (must include all intermediate nodes).
	:param parents_set: Iterable of root node names.
	:return: List of path components starting at the root and ending with *leaf*.
	:raises ValueError: If the leaf cannot be connected to any root or on cycles.
	"""
	roots_set = set(parents_set)
	if not roots_set:
		raise ValueError("Empty roots set: provide at least one root in 'parents'.")

	parent_of = parent_map(tree_dict, roots_set)

	path: List[str] = [leaf]
	current = leaf
	visited: set[str] = set()

	while current not in roots_set:
		if current in visited:
			raise ValueError(f"Cycle detected while resolving '{leaf}'.")
		visited.add(current)
		parent = parent_of.get(current)
		if parent is None:
			raise ValueError(f"Invalid tree: '{leaf}' has no path to any root (stuck at '{current}').")
		path.insert(0, parent)
		current = parent
	return path


# --- File/Dir Decision ---
def looks_like_file(node: str) -> bool:
	"""
	Heuristic: treat a node as a file if it has a non-empty suffix.
	:param node: The path name.
	:return: True, if the node looks like a file.
	"""
	return bool(Path(node).suffix)
