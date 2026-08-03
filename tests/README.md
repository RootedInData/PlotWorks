# Tests

From the directory containing `PlotWorks/`, run:

```bash
python -m unittest discover -s PlotWorks/tests -v
```

The tests cover PlotWorks branding, polished Python plotting, managed output
filenames, deterministic and generated data transformation safeguards, custom
static R validation, and custom animation validation. R is not required for the
validation-only tests.

Generated-code capabilities are available by default; tests validate their contracts and safeguards without patching feature flags.


## Render one ggplot2 case with ggrateful palettes

Run this outside the agent from the directory containing `PlotWorks/`.

Render all 16 palettes:

```bash
python PlotWorks/tests/render_case_palette_variants.py \
  --case 06-raincloud \
  --all
```

Render only selected palettes:

```bash
python PlotWorks/tests/render_case_palette_variants.py \
  --case 06-raincloud \
  --palettes bertha terrapin_station steal_your_face
```

Useful discovery commands:

```bash
python PlotWorks/tests/render_case_palette_variants.py --list-cases
python PlotWorks/tests/render_case_palette_variants.py --list-palettes
```

The script uses simulated case data, continues after an individual palette
failure, and saves images plus CSV/JSON summaries beneath
`outputs/plots/palette_tests/<case_id>/` by default. R and the packages installed
by `r_plot_library/ggplot2_cases/setup.R` are required.

## Confirmation wiring regression test

Run:

```bash
python -m unittest PlotWorks.tests.test_confirmation_wiring -v
```

This verifies that confirmation-required actions are registered directly on
`PlotWorksSupervisor` and are absent from nested specialist tool lists. It is a
structural regression test; complete the end-to-end ADK Web check below as well.

1. Start `adk web --port 8000` from the directory containing `PlotWorks/`.
2. Ask PlotWorks to preview and save a small deterministic transformation.
3. Verify that ADK Web displays a structured confirmation control.
4. Confirm it in the UI and verify that the tool returns a non-empty success payload
   containing `saved_dataset`.
5. Verify the new file exists under `outputs/data/transformed/`.
