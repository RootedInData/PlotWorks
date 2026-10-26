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


## Multi dataset and model routing checks

The suite includes isolated temporary-workspace tests for named files, workbook
sheets, folder discovery, composite/differently named join keys, all supported join
modes, missing-key policy, row growth, concatenation, unions, coalescing, interval
endpoints, source hashes, stale proposals, no-overwrite publication and rollback.
Generated-code tests verify multiple inputs/outputs, leading-zero IDs, nullable
columns, dates/categories, approved imports, runtime side-effect checks and timeout.

Model tests verify single-model operation, ordered profile/task/agent overrides,
mixed provider routing, configuration errors, retry bounds, usage telemetry,
request isolation and the rule that fallback stops after any response is yielded.
They use fake model responses and do not call paid APIs.

The offline ADK integration tests run actual nested AgentTool handoffs and root
FunctionTool confirmation on `google-adk==2.5.0`. They verify confirmation acceptance,
rejection, resume, source changes during a pending confirmation, and injected tool
context schemas. Install requirements to run these tests; adapter/integration tests
are skipped if ADK is absent. No model API key is needed for the tests. Existing
single-file transformation tests now use temporary workspaces rather than deleting
shared output directories.

From the parent directory, run just the ADK checks with:

```bash
python -m unittest PlotWorks.tests.test_adk_bundle_integration -v
```

A live provider and browser check remains useful after configuring your `.env`.
The tests validate framework execution with scripted models, not response quality,
current provider availability, or billing.

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
