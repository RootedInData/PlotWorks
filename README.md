# PlotWorks

**PlotWorks** is a modular Google ADK multi-agent workflow for inspecting local
data, performing exploratory analysis, preparing plot-ready copies of datasets,
and producing polished static or animated visualizations in Python and R.

The supervisor chooses the smallest set of specialists needed for each request.
Deterministic tools handle routine work; coding specialists are available for
unforeseen data transformations and novel R figures under explicit guardrails.

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
- Write new plotting-only R code when the experimental feature is enabled.
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
3. The user approves or rejects the save action in the ADK confirmation dialog.
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

The agent first calls `preview_data_transformations()`. Saving through
`save_data_transformations()` requires user confirmation.

### Experimental custom Python transformations

For preparation that cannot be expressed through the deterministic catalog, the
agent may write:

```python
def transform_data(data):
    # pandas/numpy transformation logic
    return transformed_dataframe
```

Enable this route in `.env`:

```env
ENABLE_CUSTOM_DATA_TRANSFORMATIONS=true
```

The validator blocks imports, file/network/system access, private attribute
access, and serialization methods. Execution occurs in a separate process and
saving requires user confirmation. This is an application-level safeguard, not a
full operating-system sandbox, so generated code should still be reviewed.

## Plotting routes

### 1. Approved R recipes

The predefined recipes under `r_plot_library/ggplot2_cases/` are the most
controlled R route. Every recipe includes simulated data for preview and testing.
Some accept a single compatible real-data table directly; others require a
plot-ready transformation or an additional adapter for matrices, networks,
hierarchies, or multiple linked tables.

Use this route for figures such as Manhattan plots, volcano-style plots,
raincloud plots, Sankey diagrams, treemaps, and the other cataloged cases.

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

### 3. Experimental custom static R plotting

When no approved recipe fits and R offers a meaningful advantage,
`RPlotDeveloperAgent` can write a new ggplot2 function.

Enable it in `.env`:

```env
ENABLE_CUSTOM_R_PLOTTING=true
```

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

#### Experimental custom gganimate

For more complex animated figures, `AnimationDeveloperAgent` can write:

```r
build_animation <- function(data) {
  # ggplot2 + gganimate code
  return(animation_object)
}
```

Enable it in `.env`:

```env
ENABLE_CUSTOM_R_ANIMATIONS=true
```

Generated code cannot load or save files, call `animate()` or `anim_save()`,
install packages, access the network, or invoke system commands. The wrapper
renders and saves the output after user confirmation.

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
| `DataTransformationAgent` | Previews and saves approved plot-ready data copies. |
| `VisualizationPlannerAgent` | Chooses approved R, `pretty_*` Python, static custom R, or animation. |
| `VisualizationAgent` | Calls deterministic polished Python plot functions. |
| `ColumnDecoderAgent` | Maps real column names to expected roles. |
| `PublicationPlotAgent` | Runs approved predefined ggplot2 recipes. |
| `RPlotDeveloperAgent` | Writes guarded plotting-only static R code. |
| `AnimationDeveloperAgent` | Produces controlled or guarded custom R animations. |
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

`google-adk>=1.14.0` is required for the action-confirmation wrappers used by
transformation and generated-code execution tools. `xlrd` is included so pandas
can read legacy `.xls` files in addition to `.xlsx` files.

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
validation/execution, static R validation, and animation validation. R rendering
is environment-dependent and should be tested separately with
`check_animation_setup()` and the approved recipe setup tools.

## Plot recipe provenance

The R plotting recipes under `r_plot_library/ggplot2_cases/` are adapted from
`ggplot2-20-journal-cases`. The corresponding MIT license is stored in that
subdirectory because it is the closest common parent of the adapted recipe code.
The PlotWorks supervisor, transformation system, Python plotting system, custom
R execution, animation system, path safeguards, and report workflow are specific
to PlotWorks.
