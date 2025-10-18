# src/sciwork/fs/openers.py

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

from ..logutil import get_logger
from .base import PathLike, PathOpsBase

LOG = get_logger(__name__)


class Open(PathOpsBase):
	"""
	Cross-platform helpers to open files/folders in the system explorer/viewer.

	Expects the host class to provide:
		- ``self._abs(path)`` from :class:`PathOpsBase`
		- ``self.dry_run`` from :class:`PathOpsBase`
		- ``Prompter().confirm(...)`` from :class:`sciwork.console.Prompter`
	"""

	@staticmethod
	def _system_open(target: Path) -> Optional[subprocess.Popen]:
		"""
		Open *target* (folder/file) in the system's file explorer/viewer.

		Returns a Popen if the opener is a regular process that we can wait on.
		On Windows, `os.startfile` is preferred and returns None (detached).

		:param target: The resolved path to open.
		:return: subprocess.Popen.
		:raises RunTimeError: Unsupported OS or no opener found.
		:raises OSError: spawn/permission errors.
		"""
		target = Path(target)
		sysname = platform.system()

		try:
			if sysname == "Windows":
				# Prefer the native API; it usually detaches (no Popen to wait on)
				try:
					os.startfile(str(target))  # ignore[attr-defined]
					return None
				except AttributeError:
					# Rare: non-CPython-on-Windows without startfile → fall back
					proc = subprocess.Popen(["explorer", str(target)])
					return proc

			elif sysname == "Darwin":
				# LaunchServices
				proc = subprocess.Popen(["open", str(target)])
				return proc

			elif sysname == "Linux":
				# Try a few common openers; `gio open <path>` needs the subcommand
				candidates: List[Tuple[str, List[str]]] = []
				if shutil.which("xdg-open"):
					candidates.append(("xdg-open", ["xdg-open", str(target)]))
				if shutil.which("gio"):
					candidates.append(("gio", ["gio", "open", str(target)]))
				if shutil.which("kde-open"):
					candidates.append(("kde-open", ["kde-open", str(target)]))
				if shutil.which("gnome-open"):
					candidates.append(("gnome-open", ["gnome-open", str(target)]))

				for _, cmd in candidates:
					try:
						proc = subprocess.Popen(cmd)
						return proc
					except Exception:
						continue

				raise RuntimeError("No system opener found (tried xdg-open/gio/kde-open/gnome-open).")

			else:
				raise RuntimeError(f"Unsupported operating system: {sysname}")
		except Exception as exc:
			LOG.exception("Failed to open system explorer for %s: %s", target, exc)
			raise

	# --- User Workflow ---
	def open_folder_and_wait(
			self,
			folder_path: PathLike,
			*,
			confirm_manual: bool = True,
			wait: bool = False,
			timeout: Optional[float] = None
	) -> Path:
		"""
		Open a folder in the system file explorer and optionally wait/confirms.

		Behavior:
			- Validates the path exists and is a directory.
			- Respects ``base_dir`` and ``dry_run``.
			- If ``wait=True``, blocks until the spawned opener process exits (not usual;
				most openers detach-on Win/Mac the opener returns immediately).
			- If ``confirm_manual=True``, asks the user to press Enter to continue.

		:param folder_path: Folder to open (absolute or relative to ``base_dir``).
		:param confirm_manual: Prompt the user to continue after opening.
		:param wait: Try to wait for the opener to exit (best-effort; many GUIs detach).
		:param timeout: Optional timeout for waiting (seconds).
		:return: The resolved absolute folder path.
		:raises FileNotFoundError: Folder does not exist.
		:raises NotADirectoryError: Path exists but is not a directory.
		:raises RuntimeError: Unsupported OS or no opener available.
		:raises OSError: OS-level failures (permissions, spawn errors).
		"""
		target = self._abs(folder_path)
		if not target.exists():
			raise FileNotFoundError(f"Folder does not exist: {target}")
		if not target.is_dir():
			raise NotADirectoryError(f"Path is not a directory: {target}")

		if getattr(self, "dry_run"):
			LOG.info("[dry-run] open folder: %s", target)
			return target.resolve()

		LOG.info("Opening folder: %s", target)
		proc = self._system_open(target)

		# Optional wait for the spawned process (best-effort)
		if wait and proc is not None:
			try:
				proc.wait(timeout=timeout)
			except subprocess.TimeoutExpired:
				LOG.warning("Opener did not exit within %.1fs for %s", timeout or 0.0, target)

		if confirm_manual:
			ask = self._pick_prompt(None, confirm=True)
			msg = "Folder is open. Press Enter (Y) to continue."
			ask(msg)
			LOG.info("User confirmed continuation.")

		return target.resolve()
