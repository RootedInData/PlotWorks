# PlotWorks

**PlotWorks** is a agentic AI workflow using the Google ADK framework for performing exploratory data analysis and creating high-quality plots in Python and R.

The supervisor agent chooses the smallest set of specialists needed for each request.
Built-in tools handle routine work; coding specialists are available for
unforeseen data transformations and novel R figures under explicit guardrails.

## Interaction model

`PlotWorksSupervisor` is the sole user-facing agent. It receives the user's
request, delegates bounded tasks to specialist agents, presents previews and
proposals, invokes confirmation-required actions, and reports the final results.
Specialist agents operate behind the supervisor as tools; they do not maintain a
separate user conversation or independently obtain approval.

## Core capabilities

PlotWorks can:

- Inspect CSV, TSV, Excel, JSON, text, DATA, BED, and BED.GZ files.
- Run deterministic pandas-based exploratory data analysis.
- Summarize BED intervals, scores, strands, and inferred chromosome sizes.
- Map inconsistent column names to likely semantic roles.
- Preview and save plot-preparation transformations without changing the source.
- Write guarded Python transformation code for unforeseen preparation needs.
- Create polished Python plots through reusable `pretty_*` functions.
- Render 20 approved ggplot2 plot recipes from simulated or supported real data.
- Apply PlotWorks-native or `ggrateful` palettes to individual recipes and compare selected palettes with a standalone test script.
- Write guarded plotting-only R code when no approved recipe fits.
- Create controlled or custom animated R/gganimate figures as GIF or MP4.
- Validate generated code and save it with run metadata.
- Run technical checks for missing, invalid, or nearly blank raster plots.
- Save Markdown analysis reports.

## Important data-protection rule

PlotWorks never transforms a source file in place.

When a plot requires filtering, recoding, aggregation, pivoting, reshaping, type
conversion, or another preparation step:

1. The proposed transformation is previewed on an in-memory copy.
2. PlotWorks describes the operations and resulting shape/columns.
3. `PlotWorksSupervisor` invokes a root-level confirmation-required tool, and the
   user approves or rejects the structured action in the ADK Web dialog.
4. An approved result is written as a new file under:

```text
outputs/data/transformed/
```

5. A metadata file records the source path, source SHA-256 hash, operations,
   before/after shape, and output path.
6. The source hash is checked again after saving to verify that the original file
   remained unchanged.

Safe subfolders are supported, for example:

```text
outputs/data/transformed/cotton/plot_ready.csv
```

The saved `plotting_input_path` can then be passed directly to PlotWorks plotting
and animation tools.

### How the confirmation dialog works

All confirmation-required write or generated-code execution tools are registered
directly on `PlotWorksSupervisor`, the user-facing agent. Specialist agents preview
or validate work and return a structured proposal; they do not invoke confirmed
writes from inside an `AgentTool`.

The supervisor then calls the corresponding tool, causing ADK Web to display its
structured confirmation control. Typing `I approve` as a normal chat message does
not replace that control. Confirm or reject the pending action in the UI. PlotWorks
never treats an empty tool payload as proof that a file was written.

## Data transformation routes

### Deterministic transformations

`DataTransformationAgent` should prefer these controlled operations:

```text
select_columns
drop_columns
rename_columns
filter_rows
convert_types
fill_missing
drop_missing
drop_duplicates
replace_values
derive_column
sort_values
aggregate
pivot_table
melt
reset_index
```

The specialist first calls `preview_data_transformations()` and returns a structured
proposal. The user-facing supervisor then invokes `save_data_transformations()` as a
root-level confirmation-required tool.

### Custom Python transformations

For preparation that cannot be expressed through the deterministic catalog, the
agent may write:

```python
def transform_data(data):
    # pandas/numpy transformation logic
    return transformed_dataframe
```

This route is available by default. PlotWorks uses it only when the
deterministic transformation catalog cannot express the required preparation.

The validator blocks imports, file/network/system access, private attribute
access, and serialization methods. The specialist returns the validated code to the
user-facing supervisor, which invokes the root-level confirmation-required execution
tool. Execution occurs in a separate process. This is an application-level safeguard,
not a full operating-system sandbox, so generated code should still be reviewed.

## Plotting routes

### 1. Approved R recipes

The predefined recipes under `r_plot_library/ggplot2_cases/` are the most
controlled R route. Every recipe includes simulated data for preview and testing.
Some accept a single compatible real-data table directly; others require a
plot-ready transformation or an additional adapter for matrices, networks,
hierarchies, or multiple linked tables.

Use this route for figures such as Manhattan plots, volcano-style plots,
raincloud plots, Sankey diagrams, treemaps, and the other cataloged cases.

#### Palette providers and defaults

Approved recipes share one palette layer rather than embedding package-specific
logic in every agent tool. PlotWorks currently supports:

- `recipe`: preserve each case's original colors.
- `plotworks`: use the built-in palettes shared with deterministic Python plots.
- `ggrateful`: use the 16 Grateful Dead-inspired palettes supplied by the
  `ggrateful` R package.

Use `list_plot_palettes()` to inspect available names and metadata. A palette
explicitly requested by the user takes precedence over the saved case default;
a saved case default takes precedence over the original recipe colors.

For one case and one palette, request a render such as:

```text
Render case 06-raincloud from simulated data using the ggrateful
terrapin_station palette and save it under palette_examples/raincloud/.
```

To compare several palettes on one selected case without using an agent, run
`tests/render_case_palette_variants.py`. It can render all 16 `ggrateful`
palettes or a named subset and writes a JSON/CSV summary beside the images.
Examples are provided in the testing section below.

To make a preferred palette the default for one approved case, PlotWorks uses
the confirmation-required `set_ggplot2_case_palette_default()` tool. The choice
is stored in the existing `plot_manifests/ggplot2_cases.json`; the R recipe does
not need to be rewritten. Resetting the provider to `recipe` restores the
original case colors.

The implementation remains intentionally lean. Python-side provider metadata
and validation live in `plot_styles/palettes.py`; R-side color retrieval and
interpolation live in `r_plot_library/shared/palettes.R`; case preferences stay
in the existing ggplot2 manifest. Adding another palette family later normally
requires extending those two palette files, not creating another tool module.

### 2. Polished Python plots

Reusable Python functions use shared PlotWorks palettes, labels, legends, figure
sizes, and export settings:

```text
pretty_histogram
pretty_barplot
pretty_scatter
pretty_lineplot
pretty_boxplot
pretty_violin
pretty_heatmap
pretty_faceted_plot
pretty_manhattan
pretty_genomic_track
create_pretty_charts
```

These functions are deterministic and preferred for routine plotting.
`create_basic_charts()` remains as a compatibility wrapper.

### 3. Custom static R plotting

When no approved recipe fits and R offers a meaningful advantage,
`RPlotDeveloperAgent` can write a new ggplot2 function.

This route is available by default and is used only when the user requests
a novel R figure or the visualization planner determines that R provides a meaningful
advantage over an approved recipe or a `pretty_*` Python function.

Generated code must define:

```r
build_plot <- function(data) {
  # plotting code
  return(plot_object)
}
```

The deterministic wrapper—not generated code—loads data and saves the figure.
Execution requires user confirmation. Generated scripts and metadata are saved
under `outputs/code/custom_r_runs/`.

### 4. Animated R plotting

PlotWorks provides two animation paths.

#### Controlled animated scatter

`render_animated_scatter()` accepts explicit x, y, time/state, color, size, and
label columns. It is the preferred route for bubble-chart-like motion through
time or states.

#### Custom gganimate

For more complex animated figures, `AnimationDeveloperAgent` can write:

```r
build_animation <- function(data) {
  # ggplot2 + gganimate code
  return(animation_object)
}
```

This route is available by default. PlotWorks generates an animation only
after the user requests one and supplies data containing an appropriate ordered
time/state variable, or approves a proposed transformation that creates a plot-ready
copy. Generated animation execution still requires user confirmation.

Generated code cannot load or save files, call `animate()` or `anim_save()`,
install packages, access the network, or invoke system commands. The wrapper
renders and saves the output after user confirmation. PlotWorks can create and
save GIF or MP4 animations from user-provided data, including animated scatter,
line, bar, point, and other ggplot2-compatible transitions when the data and
requested context support them.

Animations are written to:

```text
outputs/animations/
```

Generated scripts and run metadata are written to:

```text
outputs/code/custom_r_animation_runs/
```

## Cotton-seed animation example

The supplied cotton-seed R workflow was adapted into two PlotWorks examples:

```text
examples/transformations/cotton_seed_plot_ready.json
examples/animations/cotton_seed_animation_template.R
```

The transformation filters the long-format `Element` column, pivots `Area
harvested` and `Yield` into separate columns, converts types, removes incomplete
rows, and sorts by year/area. After approval, the saved plot-ready table can be
animated with area harvested on x, yield on y, area/country as color, area
harvested as point size, and year as the transition variable.

## Project structure

```text
PlotWorks/
├── .env.example
├── README.md
├── requirements.txt
├── agent.py
├── agent_cards.py
├── config.py
├── llm_factory.py
├── prompts.py
├── search_provider.py
├── agents/
│   └── specialists.py
├── tools/
│   ├── data_tools.py
│   ├── data_transformation_tools.py
│   ├── pretty_plot_tools.py
│   ├── visualization_planning_tools.py
│   ├── publication_plot_tools.py
│   ├── custom_r_plot_tools.py
│   ├── animation_tools.py
│   ├── plot_review_tools.py
│   ├── r_bridge.py
│   └── report_tools.py
├── plot_styles/
│   ├── plotworks_publication.mplstyle
│   ├── palettes.py
│   ├── figure_presets.py
│   ├── labeling.py
│   └── accessibility.py
├── plot_manifests/
│   └── ggplot2_cases.json
├── r_plot_library/
│   ├── setup_animations.R
│   ├── shared/
│   │   ├── theme_plotworks.R
│   │   ├── palettes.R
│   │   ├── export_presets.R
│   │   └── annotation_helpers.R
│   └── ggplot2_cases/
│       ├── LICENSE
│       ├── README.md
│       ├── R/
│       ├── cases/
│       ├── scripts/
│       └── setup.R
├── examples/
│   ├── transformations/
│   └── animations/
├── data/
├── outputs/
│   ├── data/transformed/
│   ├── plots/
│   ├── animations/
│   ├── reports/
│   └── code/
└── tests/
```

Keep source datasets in `data/`. PlotWorks-managed derivatives and outputs remain
separate under `outputs/`.

## Specialist agents

| Agent | Role |
|---|---|
| `DataIntakeAgent` | Locates and inspects source or transformed datasets. |
| `EDAAgent` | Runs deterministic exploratory statistics. |
| `DataTransformationAgent` | Previews deterministic transformations and validates generated Python proposals; the supervisor performs confirmed writes. |
| `VisualizationPlannerAgent` | Chooses approved R, `pretty_*` Python, static custom R, or animation. |
| `VisualizationAgent` | Calls deterministic polished Python plot functions. |
| `ColumnDecoderAgent` | Maps real column names to expected roles. |
| `PublicationPlotAgent` | Runs approved ggplot2 recipes and proposes persistent palette-default changes for supervisor confirmation. |
| `RPlotDeveloperAgent` | Writes and validates guarded plotting-only static R proposals for supervisor-confirmed execution. |
| `AnimationDeveloperAgent` | Produces controlled animations and validates custom R animation proposals for supervisor-confirmed execution. |
| `PlotReviewAgent` | Checks raster validity, dimensions, and likely blankness. |
| `CodePlanningAgent` | Writes non-executed Python or R plans. |
| `ReportAgent` | Produces and optionally saves a Markdown report. |
| `MethodResearchAgent` | Performs optional external method research. |

## Python setup

From the directory containing `PlotWorks/`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r PlotWorks/requirements.txt
cp PlotWorks/.env.example PlotWorks/.env
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r PlotWorks\requirements.txt
copy PlotWorks\.env.example PlotWorks\.env
```

### ADK version pin and review policy

`google-adk==2.5.0` is pinned because this is the version used to verify the
root-level action-confirmation wiring. Tool Confirmation is an experimental ADK
feature, so the pin should be reviewed regularly as confirmation behavior is
stabilized, revised, replaced, or removed upstream. Review it during planned
dependency updates and before adopting or removing other experimental ADK
features.

Do not casually replace the pin with an unbounded requirement. Test an ADK
upgrade in a separate branch or environment, review the release notes, run the
full automated suite, and complete the manual confirmation workflow below. Keep
`2.5.0` or roll back when the structured confirmation dialog, resumed tool
execution, returned payload, or output verification no longer behaves as
documented. Once the relevant ADK features are stable and PlotWorks passes its
integration tests against a newer release, update both `requirements.txt` and
this compatibility note together.

`xlrd` is included so pandas can read legacy `.xls` files in addition to `.xlsx`
files.

## Model configuration

### Gemini

```env
PROVIDER=gemini
MODEL=gemini-flash-latest
GOOGLE_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
```

### Claude through LiteLLM

```env
PROVIDER=litellm
MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=PASTE_YOUR_ANTHROPIC_API_KEY_HERE
```

### OpenAI through LiteLLM

```env
PROVIDER=litellm
MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE
```

Here, `PROVIDER=litellm` identifies ADK's model adapter. The provider prefix in
`MODEL` identifies the company serving the model.

## R setup

R plotting requires `Rscript` and packages installed in the same WSL/Linux or
operating-system environment where ADK runs.

```bash
Rscript --version
```

### Recommended WSL/Linux dependency route

Install available Ubuntu binaries first for difficult network, spatial, and
animation dependencies:

```bash
sudo apt update

for pkg in \
  r-cran-igraph \
  r-cran-tidygraph \
  r-cran-ggraph \
  r-cran-graphlayouts \
  r-cran-sf \
  r-cran-units \
  r-cran-lwgeom \
  r-cran-circlize \
  r-cran-treemapify \
  r-cran-gganimate \
  r-cran-gifski \
  r-cran-transformr \
  r-cran-av
do
  if apt-cache show "$pkg" >/dev/null 2>&1; then
    sudo apt install -y "$pkg"
  fi
done
```

Then run:

```bash
cd PlotWorks/r_plot_library/ggplot2_cases
Rscript setup.R
cd ../..
Rscript setup_animations.R
```

`setup.R` installs the CRAN dependencies and uses the lighter `remotes` package
to install `RandomForestz/ggrateful` from GitHub when it is not already
available. Run the setup again after pulling an update that adds another
external R palette provider.

### Personal R library

If the system library is not writable:

```bash
mkdir -p ~/R/plotworks_library
echo 'R_LIBS_USER=~/R/plotworks_library' >> ~/.Renviron
export R_LIBS_USER=~/R/plotworks_library
```

### Updating `ggraph` for a newer `ggplot2`

If Ubuntu provides an older `ggraph` than the user-installed `ggplot2`, install
current `ggraph` into the user library:

```bash
export R_LIBS_USER=~/R/plotworks_library

Rscript -e '
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
install.packages(
  "ggraph",
  repos = "https://cloud.r-project.org",
  dependencies = TRUE,
  lib = Sys.getenv("R_LIBS_USER")
)
' 2>&1 | tee ggraph_install.log
```

## Running PlotWorks

Run ADK from the parent directory containing `PlotWorks/`:

```bash
adk run PlotWorks
```

For the browser interface:

```bash
adk web --port 8000
```

If the parent directory contains multiple ADK apps, select `PlotWorks` in the
web interface.

## Example palette requests

List the available palette providers and names:

```text
List the palettes available to approved ggplot2 recipes, including whether each
supports an official continuous or diverging scale.
```

Compare palettes for one case outside the agent:

```bash
python PlotWorks/tests/render_case_palette_variants.py \
  --case 06-raincloud \
  --all
```

Or render only selected palettes:

```bash
python PlotWorks/tests/render_case_palette_variants.py \
  --case 06-raincloud \
  --palettes bertha terrapin_station steal_your_face
```

Persist a favorite as a case default:

```text
Make terrapin_station the default ggrateful palette for case 06-raincloud.
Explain the persistent manifest change and ask for my confirmation before
saving it.
```

An explicit palette in a later request still overrides that saved default.

## Example transformation-to-animation request

```text
Inspect FAOSTAT_data_en_12-8-2024.xls. I want an animated scatter plot of
area harvested versus yield over Year, colored by Area and sized by area
harvested. First preview the necessary transformation from the long Element/
Value structure into a plot-ready table. Do not alter the source. Ask for my
approval before saving the transformed data, then create the GIF.
```

PlotWorks should preview a pivot similar to the JSON example, pause for
confirmation, save the new table under `outputs/data/transformed/`, and then
create the animation under `outputs/animations/`.

## Path guidance

The safest option is to place source inputs in:

```text
PlotWorks/data/
```

If ADK runs in WSL, use WSL-readable paths such as `/mnt/c/...`, not Windows
paths such as `C:\...`.

Absolute external paths are disabled by default:

```env
ALLOW_ABSOLUTE_DATA_PATHS=false
```

Absolute paths returned by PlotWorks for managed source/transformed files remain
usable. Other external absolute paths require the flag to be enabled.

Plot output parameters accept filenames only. Data transformation output names
may include safe relative subfolders under `outputs/data/transformed/`.

## BED support

The first three BED columns are interpreted as:

```text
chrom
chromStart
chromEnd
```

Optional BED fields are recognized through BED12. PlotWorks can summarize
interval counts, lengths, scores, strands, and inferred chromosome sizes.

## Tests

From the parent directory:

```bash
python -m unittest discover -s PlotWorks/tests -v
```

The test suite covers branding, polished Python plotting, safe output paths,
source-preserving deterministic transformations, custom transformation
validation/execution, static R validation, animation validation, palette-provider
metadata, case defaults, safe palette output paths, the standalone selected-case
palette runner, and palette-aware R recipe wiring. R rendering is
environment-dependent and should be tested separately with
`check_animation_setup()` and the approved recipe setup tools.

### End-to-end confirmation test

The automated confirmation-wiring test verifies that protected actions are
registered directly on `PlotWorksSupervisor`. It does not prove that ADK Web
displays and resumes the interactive confirmation event in your local
environment. Test that behavior manually after installation and after every ADK
version change.

#### 1. Verify the active environment

```bash
cd /mnt/c/Users/bdjor/GitHub
source PlotWorks/.venv/bin/activate
python -m pip show google-adk | grep -E 'Version|Location'
which python
which adk
```

The version should be `2.5.0`, and the reported package, Python executable, and
ADK executable should all resolve inside `PlotWorks/.venv/`.

#### 2. Run the focused wiring test and full suite

```bash
python -m unittest discover \
  -s PlotWorks/tests \
  -p 'test_confirmation_wiring.py' \
  -v

python -m unittest discover -s PlotWorks/tests -v
```

#### 3. Record the original file hash and clear the test destination

```bash
sha256sum PlotWorks/data/demo_general.csv \
  > /tmp/plotworks_demo_general.before.sha256

rm -rf PlotWorks/outputs/data/transformed/confirmation_test
```

#### 4. Start ADK Web from the parent directory

```bash
adk web --port 8000
```

Use this deterministic test prompt:

```text
Inspect demo_general.csv. Preview a deterministic aggregation grouped by
treatment and location that reports cell count plus the mean, median, and
standard deviation of yield_kg. After showing the preview, have
PlotWorksSupervisor invoke the confirmed save action and save the result as
confirmation_test/treatment_location_summary.csv. Do not treat a typed approval
as confirmation; wait for the ADK Web confirmation control.
```

Expected behavior:

1. `DataTransformationAgent` returns a preview and structured proposal.
2. `PlotWorksSupervisor` invokes `save_data_transformations()`.
3. ADK Web displays its structured confirmation control.
4. Clicking **Confirm** resumes the call.
5. The returned tool payload is non-empty and includes `status: success`, a
   saved-dataset path, a metadata path, and `source_unchanged: true`.

Verify the files and source hash:

```bash
ls -l \
  PlotWorks/outputs/data/transformed/confirmation_test/

python -m json.tool \
  PlotWorks/outputs/data/transformed/confirmation_test/\
  treatment_location_summary.csv.metadata.json

sha256sum -c /tmp/plotworks_demo_general.before.sha256
```

#### 5. Test rejection

Repeat the request with the output name
`confirmation_test/rejected_should_not_exist.csv`, then select **Reject** in the
structured confirmation control. Verify that neither the dataset nor its
metadata file exists:

```bash
test ! -e \
  PlotWorks/outputs/data/transformed/confirmation_test/\
  rejected_should_not_exist.csv
```

#### 6. Test generated Python through the same root confirmation path

```text
Using demo_general.csv, create a transformed copy with a new
yield_z_within_treatment column calculated from the treatment-specific mean and
standard deviation of yield_kg. This requires generated Python rather than the
deterministic operation catalog. Validate the code, present the proposal, then
have PlotWorksSupervisor invoke the confirmed execution action and save it as
confirmation_test/custom_yield_z.csv. Wait for the ADK Web confirmation
control.
```

After confirmation, verify that the output and metadata exist and that a
generated script plus run metadata were saved beneath:

```text
outputs/code/data_transform_runs/
```

#### 7. Inspect the ADK server log when a call stalls

Look for the requested tool name, the confirmation event, the resumed tool call,
and the final function response. A successful run must not end with an empty
payload, claim success without a saved file, or leave the call indefinitely
pending. Preserve the log and the full tool response when reporting a failure.

The confirmation fix passes its intended acceptance test only when confirmation,
rejection, deterministic execution, generated execution, returned payloads,
managed outputs, metadata, and source preservation all behave correctly.

## Plot recipe provenance

The R plotting recipes under `r_plot_library/ggplot2_cases/` are adapted from
`ggplot2-20-journal-cases`. The corresponding MIT license is stored in that
subdirectory because it is the closest common parent of the adapted recipe code.
The PlotWorks supervisor, transformation system, Python plotting system, custom
R execution, animation system, palette orchestration, path safeguards, and report
workflow are specific to PlotWorks. The optional `ggrateful` dependency is an
MIT-licensed external package and remains governed by its own license.
