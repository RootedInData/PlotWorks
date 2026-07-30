# PlotWorks examples

- `transformations/cotton_seed_plot_ready.json` converts a long FAOSTAT-style
  table into one row per area and year with separate `area_harvested` and `yield`
  columns. Preview it before approving a saved transformed copy.
- `animations/cotton_seed_animation_template.R` follows the custom animation
  contract and demonstrates `transition_time()`, `shadow_wake()`, and fades.

The source dataset is never edited. Save the approved transformed table under
`outputs/data/transformed/`, then pass that saved path to the animation tool.
