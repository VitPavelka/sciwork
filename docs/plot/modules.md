# Plot module guide

This guide dives into the mixin modules that make up `sciwork.plot.Plot`. Each
section highlights the primary responsibilities and the headline helpers exposed
by the mixin.

## Base utilities (`sciwork.plot.base`)

Responsible for figure lifecycle management, cached data limits, and SciWork's
logging integration.

### `create_grid_layout(nrows, ncols)`
Creates a `matplotlib.figure.Figure` with an accompanying grid of subplots sized
according to the `Plot` instance's `figsize`. Both dimensions must be positive
integers, otherwise a `ValueError` is raised.

### `add_inset(min_ax, *, left, bottom, width, height)`
Adds inset axes positioned using figure-fraction coordinates. Coordinates are
validated so the inset remains within the parent axes; invalid dimensions raise
`ValueError`.

### `show_plot()`
Applies `tight_layout()` and displays the figure via `pyplot.show()`. Useful as
the final call in interactive workflows.

### `save_plot(filename, *, dpi=300, format="png")`
Persists the current figure to disk, ensuring the requested file extension and
dpi are valid. Logs the resolved path through SciWork's logger before returning
the filename.

## Drawing helpers (`sciwork.plot._drawing`)

Contains primitives for lines, error envelopes, 2D charts, and 3D scatter plots.

### `draw_horizontal_line(y, ...)` and `draw_vertical_line(x, ...)`
Convenience wrappers around `axhline` and `axvline` that accept legend labels,
opacity, and style arguments.

### `plot_std_deviation(x, y, yerr, ...)`
Draws symmetric error bars to visualize standard deviation (or any symmetric
uncertainty band). Sequence length mismatches raise `ValueError`.

### `plot_1d(data, ...)`
Plots a single sequence against its index, updating cached data limits for later
reuse.

### `plot_2d(x, y, *, plot_type=...)`
Supports scatter, line, moving-average, histogram, and bar charts. Moving
average plots delegate smoothing to `MathStat.moving_average`. Missing required
data or unknown plot types raise `ValueError`.

### `plot_3d(x, y, z, ...)`
Ensures 3D axes exist before plotting a scatter cloud. Sequence length
mismatches raise `ValueError`.

## Layout helpers (`sciwork.plot.layout`)

Encapsulates axis labels, color themes, limits, and spine placement.

### `set_plot_labels(...)`
Assigns axis labels and title while supporting per-axis offsets through
`ScaledTranslation`. Passing a `zlabel` on non-3D axes triggers an
`AttributeError` so mistakes surface early.

### `toggle_dark_mode(dark_mode=True, *, ax=None)`
Switches between light and dark color palettes for the selected axes and their
figure background.

### `set_axes_linewidth(linewidth=1.0, *, ax=None)`
Synchronizes spine thickness across all visible axes spines.

### `set_axes_limits(...)`
Applies numeric boundaries or the special string `"data"` to reuse cached
limits. Missing cached limits cause a `ValueError`, while requesting `z`
limits on a 2D axes raises `AttributeError`.

### `set_title_size(size=14.0, *, ax=None)`
Resizes the axes' title using Matplotlib's `set_fontsize` API.

### `set_axis_label_size(size=12.0, *, axis="both", ax=None)`
Targets one or multiple axis labels and updates their font sizes.

### `set_axis_position(axis="y", position=0.0, *, ax=None)`
Repositions the specified spine so it intersects the opposing axis at a data
coordinate. Invalid axis names raise `ValueError`.

## Decorative utilities (`sciwork.plot._decor`)

Focuses on aesthetic touches such as grids, legends, and text annotations.

### `set_grid(...)`
Enables major and/or minor grid lines with custom colors, transparency, and
line styles. Rejects invalid axis specifiers.

### `set_legend(...)`
Creates a legend with ordering, filtering, and typography controls. When no
handles remain after filtering, the method logs a warning and returns `None`.

### `add_custom_text(...)`
Places free-form text inside the axes. Accepts named positions or explicit
coordinates and optional styling hints like bold or italic.

## Tick and scale helpers (`sciwork.plot._ticks`)

Provides tick styling and axis-scaling utilities shared across plot types.

### `set_tick_linewidth(...)`
Applies consistent tick widths across selected axes. An alias
`set_ticks_linewidth` is kept for backwards compatibility.

### `set_tick_length(...)`
Adjusts major and/or minor tick lengths using a single call.

### `set_ticks_invisible(...)`
Hides both tick marks and their labels for the selected axes.

### `set_minor_ticks(num_minor_ticks=1, ...)`
Configures minor tick locators for linear and logarithmic axes. Rejects values
below one.

### `set_custom_ticks(tick_values, ...)`
Installs explicit tick positions and adjusts major formatters according to the
axis scale.

### `set_custom_tick_labels(tick_labels, ...)`
Replaces visible tick labels. Length mismatches trigger a `ValueError`.

### `set_log_scale(log_x=False, log_y=False, log_z=False, ...)`
Switches each axis to logarithmic scaling when requested. The z-axis path reuses
the 3D guard from the layout mixin.

### `reverse_axis(reverse_x=False, reverse_y=False, reverse_z=False, ...)`
Flips the direction of selected axes while preserving current limits.

### `scale_axis_labels(scale_factor=None, method="simple", ...)`
Multiplies tick labels by a constant or shifts orders of magnitude. Enforces a
positive multiplier for logarithmic scales.

### `set_tick_label_size(size=10.0, ...)`
Applies a uniform font size to tick labels and offset text, refreshing the
render cache afterward. 