# Stats utilities

`sciwork.stats` bundles a handful of numeric helpers focused on quick, "good
enough" exploration of one-dimensional series or small tabular datasets. The
module is intentionally lightweight-it leans on NumPy/PanDas when available but
keeps a Python-only fallback for callers who just need the convenience wrappers.

The module contains:

- **Coercion helpers** such as `coerce_vector` that massage different containers
  (lists, NumPy arrays, Series, DataFrames, mappings) in to numeric 1D arrays.
- **Descriptive statistics** via `describe_1d`, `describe_df`, and `percentiles`.
- **Transform utilities** such as `log_values`, `power_values` and 
`moving_average` for small-scale preprocessing.
- **Quality-of-life helpers** including the `normal_round` half-up rounding helper.
- **`MathStat`**, a thin stateful wrapper over the above helpers for users who
prefer method chaining while working with a single dataset.

## Quick start

The quickest entry point is the `MathStat` class exposed at the top level of the
package:

```python
from sciwork import MathStat

ms = MathStat([1, 2, 3, 100])
summary = ms.describe()
outliers = ms.outliers()
log_values = ms.log(base=10)
```

For module-level functions (stateless usage) access them via the `stats`
namespace:

```python
from sciwork import stats

vector = stats.coerce_vector([1, "2", 3.5])
pct = stats.percentiles(vector, [5, 50, 95])
```

Head over to [MathStat workflows](mathstat.md) for a deeper dive into the class
API and how it composes the building blocks listed above.