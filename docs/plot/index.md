# Plot utilities

`sciwork.plot` offers a Matplotlib-powered plotting toolkit that mirrors the
package's emphasis on lazy imports and composable helpers. The module keeps
Matplotlib behind the usual Sciwork lazy import layer, so importing
`Plot` does not immediately load the heavy plotting stack.

Use the module when you want:

- to get rid of doing the same thing over and over again in Microsoft Excel
or Google Sheets;
- A reusable `Plot` manager that centralizes figure creation and styling
decisions;
- Quality-of-life helpers that wrap repetitive Matplotlib patterns such as
moving average, grids, legends, and plot annotations.

## Quickstart

```python
from sciwork import Plot

plot = Plot(figsize=(8, 5))
x = [0, 1, 2, 3, 4]
y = [1.0, 1.5, 2.0, 2.5, 3.0]

plot.plot_2d(x, y, plot_type="line", label="experiment")
plot.set_plot_labels(title="Calibration", xlabel="Time (s)", ylabel="Voltage (V)")
plot.set_legend()
plot.save_plot("calibration")
```

Head to [Plot workflows](plot.md) for tips on composing patterns and to see
how the helper interplays with other Sciwork modules.

## Module overview

| Module                         | Responsibility                                                                    | Helpers                                                                                                                                                                                                       |
|--------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `sciwork.plot.base.BasePlot`   | Manages figure lifecycle, cached limits, and SciWork logging integration.         | `create_grid_layout`, `add_inset`, `show_plot`, `save_plot`                                                                                                                                                   |
| `sciwork.plot.drawing.Drawing` | Collects drawing primitives and MathStat-powered helpers.                         | `draw_horizontal_line`, `draw_vertical_line`, `plot_std_deviation`, `plot_1d`, `plot_2d`, `plot_3d`                                                                                                           |
| `sciwork.plot.layout.Layout`   | Controls labels, limits, and spine positioning across 2D/3D axes.                 | `set_plot_labels`, `toggle_dark_mode`, `set_axes_linewidth`, `set_axes_limits`, `set_title_size`, `set_axis_label_size`, `set_axis_position`                                                                  |
| `sciwork.plot.decor.Decor`     | Applies presentation-focused tweaks such as grids, legends, and free-form text.   | `set_grid`, `set_legend`, `add_custom_text`                                                                                                                                                                   |
| `sciwork.plot.ticks.Ticks`     | Provides tick styling and axis scaling utilities for linear or logarithmic plots. | `set_tick_linewidth`, `set_tick_length` , `set_ticks_invisible`, `set_minor_ticks`, `set_custom_ticks`, `set_custom_tick_labels`, `set_log_scale`, `reverse_axis`, `scale_axis_labels`, `set_tick_label_size` |

Each section is documented in detail in the [Plot module guide](modules.md).

!!! tip
    MkDocs supports standard Markdown image syntax, so future guides can embed
    screenshots or generated figures using ``![Caption](path/to/image.png)``.
    