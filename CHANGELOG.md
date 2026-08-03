# Changelog

## Root-level ADK confirmation wiring

- Moved all confirmation-required write and generated-code execution tools from
  nested specialist `AgentTool` instances to the user-facing `PlotWorksSupervisor`.
- Changed DataTransformationAgent into a preview/validation specialist that returns
  structured deterministic or generated-Python proposals without writing files.
- Applied the same root-level confirmation boundary to persistent palette defaults,
  custom static R execution, and custom R animation execution to prevent equivalent
  nested confirmation failures.
- Updated prompts and documentation to distinguish ADK's structured confirmation
  event from a free-text approval message.
- Pinned `google-adk==2.5.0`, the version verified in the PlotWorks virtual environment.
- Added structural regression tests for confirmation-tool placement.

## Selected-case ggrateful palette test runner

- Removed the agent-facing `render_all_ggplot2_palette_variants()` function and
  all imports, registrations, prompts, documentation, and tests tied to it.
- Added `tests/render_case_palette_variants.py`, a standalone command-line test
  that renders one selected ggplot2 case with all 16 `ggrateful` palettes or a
  user-selected subset.
- Kept individual palette rendering, palette validation, case defaults, and the
  shared Python/R palette architecture unchanged.

## Shared ggplot2 palette providers

- Added the 16 `ggrateful` palette names and scale metadata to the existing
  `plot_styles/palettes.py` provider registry without copying package-owned hex
  colors into Python.
- Expanded the existing `r_plot_library/shared/palettes.R` helper to retrieve
  `ggrateful` colors at render time, use official gradients when available, and
  interpolate comparison gradients when needed.
- Refactored all 20 approved ggplot2 cases to use the shared palette layer while
  preserving their original colors as the default.
- Added explicit palette overrides, safe output subfolders, palette precedence,
  and persistent confirmation-required case defaults in the existing manifest.
- Updated R setup, prompts, agent tools, documentation, and tests. The design
  remains extensible through the existing Python and R palette files rather
  than a new palette-management module.

## Always-available generated plotting and transformation capabilities

- Removed the `ENABLE_CUSTOM_DATA_TRANSFORMATIONS`, `ENABLE_CUSTOM_R_PLOTTING`,
  and `ENABLE_CUSTOM_R_ANIMATIONS` feature switches.
- Custom Python transformations, novel static R plots, and custom gganimate
  plots are now available by default.
- Preserved ADK user confirmation, generated-code validation, managed output
  paths, source-file protection, execution timeouts, and code-size limits.
- Updated prompts, agent cards, validation tests, `.env.example`, and the README
  to describe request/approval-based behavior instead of environment toggles.
- Expanded the README animation section to explain GIF/MP4 creation and saving
  from user-supplied, time- or state-aware data.

## PlotWorks transformation and animation update

- Renamed the application, package, supervisor, documentation, styles, prompts,
  and R helpers from the previous project-name variants to **PlotWorks**.
- Added source-preserving deterministic data transformations with preview,
  provenance metadata, SHA-256 verification, safe output subfolders, and ADK
  confirmation before saving.
- Added guarded custom Python transformations for plot-preparation cases that
  the deterministic operation catalog cannot express.
- Added controlled animated scatter plots and guarded custom R/gganimate
  figures with GIF and MP4 output.
- Added a cotton-seed transformation example and custom animation template
  adapted to the PlotWorks data and rendering contracts.
- Added new output directories, environment settings, dependencies,
  documentation, and tests.
