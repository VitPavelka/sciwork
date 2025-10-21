# Plot workflows

The `Plot` class offers a single place to orchestrate figure creation, axis
styling, and drawing primitives. Each method returns the affected `Axes` object
so you can continue chaining vanilla Matplotlib calls when needed.

## Controlling the figure lifecycle

`Plot` initializes an internal figure and primary axes using `pyplot.subplots`.
It exposes helpers for creating additional layouts or insets without repeating
Matplotlib boilerplate:

```python
from sciwork import Plot

plot = Plot()
fig, (ax_left, ax_right) = plot.create_grid_layout(nrows=1, ncols=2)
plot.add_inset(ax_left, left=0.5, bottom=0.5, width=0.4, height=0.35)
```

Saving or displaying the figure runs through SciWork's logger, so you get an
informative message when files are written:

```python
plot.save_plot("report")  # -> INFO Saved figure to report.png
```

## Axis labeling and ticks

`Plot` centralizes a range of axis customizations:

- `set_plot_labels` shifts labels using `ScaledTranslation`, handy for dense
subplots.
- `set_tick_linewidth`, `set_tick_length`, and `set_tick_label_size` align tick
styling across multiple axes.
- `set_minor_ticks` and `scale_axis_labels` handle both linear and logarithmic
scales with input validation.

These helpers update the cached data limits, so you can later call
`set_axes_limits(xmin="data", xmax="data")` to reuse the observed extents.

## Drawing data with MathStat helpers

The drawing primitives use `MathStat` internally for the moving-average branch.
That keeps the smoothing logic consistent with the stats module while allowing a
single call to generate the visualization:

```python
from sciwork.imports import np  # lazy import

x = np.arange(0, 100)
y = np.sin(x / 10) + np.random.normal(scale=0.05, size=x.size)

plot.plot_2d(x, y, plot_type="scatter", alpha=0.4, label="raw")
plot.plot_2d(x, y, plot_type="moving_average", ma_window=7, label="trend")
plot.set_legend()
plot.show()
```

All plotting methods update internal `data_limits`, enabling data-driven
`set_axes_limits(..., xmin="data", xmax="data")` calls later in the pipeline.