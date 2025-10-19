# src/sciwork/stats/__init__.py
"""
Lightweight math and stats utilities split by concern.
"""

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
	# functions
	"coerce_vector",
	"describe_1d", "describe_df",
	"percentiles", "outliers_iqr",
	"moving_average", "log_values", "power_values",
	"normal_round",
	# class
	"MathStat"
]


def __getattr__(name: str):
	mod_of = {
		"coerce_vector": "sciwork.stats.coerce",
		"describe_1d": "sciwork.stats.describe",
		"describe_df": "sciwork.stats.describe",
		"percentiles": "sciwork.stats.describe",
		"outliers_iqr": "sciwork.stats.outliers",
		"moving_average": "sciwork.stats.transforms",
		"log_values": "sciwork.stats.transforms",
		"power_values": "sciwork.stats.transforms",
		"normal_round": "sciwork.stats.rounding",
		"MathStat": "sciwork.stats.mathstat"
	}
	if name in mod_of:
		mod = import_module(mod_of[name])
		return getattr(mod, name)
	raise AttributeError(f"module 'sciwork.stats' has no attribute {name!r}")


if TYPE_CHECKING:
	from .coerce import coerce_vector
	from .describe import describe_1d, describe_df, percentiles
	from .outliers import outliers_iqr
	from .transforms import moving_average, log_values, power_values
	from .rounding import normal_round
	from .mathstat import MathStat
