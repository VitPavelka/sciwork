# Lazy imports

## Basic and implemented usage

```python
from sciwork import np, pd

# numpy is actually imported here
arr = np.array([1, 2, 3])

# pandas here:
df = pd.DataFrame({"x": [1, 2, 3]})
```

## Creating a custom import

```python
from sciwork import lazy_module

sk = lazy_module("sklearn", install="pip install scikit-learn", reason="ML pipelines")
model = sk.linear_model.LinearRegression()  # sklearn is imported here
```
