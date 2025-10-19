from sciwork import MathStat

# Mathstat workflows

`Mathstat` wraps the stateless helpers from `sciwork.stats` into a stateful,
method-oriented facade. Instantiate it with your data once, then call whichever
statistics or transforms you need without repeatedly passing the data around.

```python
from sciwork.stats import Mathstat, normal_round, moving_average

ms = MathStat([1, 2, 3, 100])
print(ms.describe()["mean"])  # 26.5
print(ms.percentiles([25, 50, 75]))  # array([...])
print(normal_round(1.25, decimals=1))  # 1.3 (half-up rounding)
print(moving_average(ms, window_size=2))  # array([...])
```

## Supported inputs

`Mathstat` accepts anything `coerce_vector` can handle: 

- Sequences or numeric values (lists/tuples)
- NumPy arrays and Pandas Series
- Dictionaries or mappings (values are read in insertion order)
- Pandas DataFrames — pass `column="name"` or `column=index` to focus on a
single column when necessary

When you pass a multi-column DataFrame, vector-based methods require the 
`column` argument. `describe_table` is the only method so far that expects
a DataFrame and operates column-wise by default.

## Frequently used helpers

### `describe`

Produces a dictionary with min/max/sum/mean/median/std/coeff_var. The method
internally calls :func:`sciwork.stats.describe_1d`, so the keys, behavior, and
NaN handling match the stateless helpers exactly.

```python
summary = ms.describe()
print(summary["std"])  # sample standard deviation (ddof=1)
```

### `percentiles`

Provide a list of percentile values and get a NumPy array back. Percentiles are
NaN-aware and rely on :func:`numpy.nanpercentile` under the hood.

### `outliers`
Detects outliers using the interquartile range (IQR) heuristic.

```python
ms = MathStat([1, 2, 3, 100])
print(ms.outliers(threshold=1.5))  # array([100.])
```

### Transforms `log`, `power`, `moving_average`

These helpers provide quick preprocessing steps. All of them accept optional
`column` and reuse the stateless implementations from `sciwork.stats.transforms`.

```python
smoothed = ms.moving_average(window_size=3)
scaled = ms.power(base=10)
```

### `describe_table`

When you initialize `Mathstat` with a DataFrame, you can get a multi-column
summary without specifying column selectors:

```python
import pandas as pd

ms = MathStat(pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]}))
print(ms.describe_table().loc[:, ("mean", slice(None))])
```

## Rounding helper: `normal_round`

`normal_round` is a small utility that implements **half-up** rounding semantics.
It is re-exported at the package root next to `Mathstat` and `moving_average`
so you can keep your statistical helpers together.

```python
from sciwork import normal_round

normal_round(0.5)  # 1.0
normal_round(1.25, decimals=1)  # 1.3
normal_round(-1.25, 1)  # -1.2
```

Unlike Python's ``round`` builtin (banker's rounding) the half-up strategy always
pushes ``0.5`` away from zero, which is ofter preferable for reporting.