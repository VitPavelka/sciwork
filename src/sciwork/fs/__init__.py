# src/sciwork/fs/__init__.py
from importlib import import_module
from typing import TYPE_CHECKING

# Map: public name -> "module_path:attr_name"
_MAP = {
    "PathOps":     "sciwork.fs.pathops:PathOps",
    "Paths":       "sciwork.fs.paths:Paths",
    "Dirs":        "sciwork.fs.dirs:Dirs",
    "Create":      "sciwork.fs.create:Create",
    "Delete":      "sciwork.fs.deleter:Delete",
    "Transfer":    "sciwork.fs.transfer:Transfer",
    "Open":        "sciwork.fs.openers:OpenN",
    "Archives":    "sciwork.fs.archives:Archives",
    "Select":      "sciwork.fs.selector:Select",
    "GetContents": "sciwork.fs.getcontents:GetContents",
    "Load":        "sciwork.fs.loaders:Load",
    "TreeOps":     "sciwork.fs.trees:TreeOps",
}

__all__ = list(_MAP.keys())


def __getattr__(name: str):
    try:
        spec = _MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module 'sciwork.fs' has no attribute {name!r}") from exc

    mod_path, _, attr = spec.partition(":")
    mod = import_module(mod_path)
    return getattr(mod, attr)


# --- help static type checkers without eager imports ---
if TYPE_CHECKING:
    from .pathops import PathOps
    from .paths import Paths
    from .dirs import Dirs
    from .create import Create
    from .delete import Delete as Delete
    from .transfer import Transfer
    from .open import Open as Open
    from .archives import Archives
    from .select import Select as Select
    from .getcontents import GetContents
    from .load import Load
    from .trees import TreeOps
