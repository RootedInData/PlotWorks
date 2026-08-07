# PlotWorks

**PlotWorks** is a agentic AI workflow using the Google ADK framework for performing exploratory data analysis and creating high-quality plots in Python and R.

The supervisor agent chooses the smallest set of specialists needed for each request.
Built-in tools handle routine work, while coding specialists stand by for
unforeseen coding requests and for creating novel R figures.

## Interaction model

`PlotWorksSupervisor` is the sole user-facing agent. Specialist agents operate behind
the supervisor as tools. `PlotWorksSupervisor` receives the user's request, delegates tasks to specialists, 
presents previews and proposals, and reports the final results.

## Core capabilities

PlotWorks can:

- Detect CSV, TSV, Excel, JSON, text, DATA, BED, and BED.GZ files.
- Run pandas-based exploratory data analysis using deterministic functions and code generated on the fly.
- Summarize BED intervals, scores, strands, and inferred chromosome sizes.
- Map inconsistent column names to likely semantic roles.
- Write Python code for transforming data in unforeseen situations.
- Create polished Python plots using the `pretty_*` functions.
- Render 20 ggplot2 plot bioinformatics recipes from simulated or real data.
- Apply a selection of palettes to plots.
- Write R code for plotting when no recipe fits.
- Create custom animated R/gganimate figures as GIF or MP4.
- Validate generated code and save it with run metadata.
- Run technical checks for missing, invalid, or nearly blank raster plots.
- Save Markdown analysis reports.

## Important data-protection rule

PlotWorks never transforms a source file in place.

When a plot requires transformation, `PlotWorksSupervisor` invokes a confirmation tool, and the user approves or rejects the action in the ADK Web dialog. Any approved results are written as a new file under:

```text
outputs/data/transformed/
```

A metadata file records the source path, source SHA-256 hash, operations, before/after shape, and output path.

### How the confirmation dialog works

All write or custom-code execution tools are registered
directly on `PlotWorksSupervisor`. Specialist agents preview
and validate work and return a proposal, but they do not invoke
writes from inside an `AgentTool`.

The supervisor then calls the corresponding tool, causing ADK Web to display its
confirmation control. Providing approaval as a normal chat message does
not replace that control. Confirm or reject the pending action in the UI.

## Data transformation routes

### Deterministic transformations

`DataTransformationAgent` has several preset operations:

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

The specialist first calls `preview_data_transformations()` and returns a
proposal. The supervisor then invokes `save_data_transformations().

### Custom Python transformations

For data preparation that cannot be expressed through the catalog, the
agent may write:

```python
def transform_data(data):
    # pandas/numpy transformation logic
    return transformed_dataframe
```

The validator blocks imports, file/network/system access, private attribute
access, and serialization methods. The specialist returns the validated code to the
supervisor, which invokes the execution tool. Execution occurs in a separate process. 
This is an application-level safeguard, not a true sandbox, so generated code should still be reviewed.

## Plotting routes

### 1. R bioinformatics recipes

Predefined bioinformatics recipes are available and can be applied to the appropriate inputs. Note, some recipes require several input files. Every recipe includes simulated data for preview and testing.
Some accept a single data table directly; others require a
transformation or an additional adapter for matrices, networks,
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

request rendering of a specific case drawn with a palette of your choice such as:

```text
Render case 06-raincloud from simulated data using the ggrateful
terrapin_station palette and save it under palette_examples/raincloud/.
```

To compare several palettes on one selected case without using an agent, run
`tests/render_case_palette_variants.py`. It can render all 16 `ggrateful`
palettes or a named subset and writes a JSON/CSV summary beside the images.
Examples are provided in the testing section below.

To make a preferred palette the default for one approved case, PlotWorks uses
`set_ggplot2_case_palette_default()`. The choice
is stored in `plot_manifests/ggplot2_cases.json`. Resetting the provider to `recipe` restores the
original case colors.

The implementation remains intentionally lean. Python-side provider metadata
and validation live in `plot_styles/palettes.py`; R-side color retrieval and
interpolation live in `r_plot_library/shared/palettes.R`; case preferences stay
in the existing ggplot2 manifest. Adding another palette family later normally
requires extending those two palette files.

### 2. Python plots

Python plotting functions use PlotWorks palettes, labels, legends, figure
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

### 3. Custom R plotting

When no ggplot2 recipe fits and R offers a meaningful advantage,
`RPlotDeveloperAgent` can write a new ggplot2 function.

This route is available by default and is used only when the user requests
a novel R figure or the visualization planner determines that R provides a meaningful
advantage over a recipe or a `pretty_*` Python function.

Generated code must define:

```r
build_plot <- function(data) {
  # plotting code
  return(plot_object)
}
```

Newly Generated scripts and metadata are saved under `outputs/code/custom_r_runs/`.

### 4. Animated R plotting

PlotWorks provides support for creating animated plots (GIF or MP4) with two paths:

#### Animated scatter

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

PlotWorks can create animations including animated scatter,
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

## Installation

PlotWorks needs Python, R, and at least one supported model API key. Install Git
if you are cloning the repository. MP4 animation also requires FFmpeg on your
system path.

The project pins `google-adk==2.5.0`, the version used to verify its confirmation
workflow. Install from `requirements.txt` instead of choosing ADK packages one
by one; dependency roulette is a poor visualization technique.

### Linux, macOS, or WSL

From the cloned repository:

```bash
cd PlotWorks
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Install the R plotting packages:

```bash
Rscript r_plot_library/ggplot2_cases/setup.R
Rscript r_plot_library/setup_animations.R
```

### Windows PowerShell

From the cloned repository:

```powershell
Set-Location PlotWorks
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Make sure `Rscript.exe` is available from PowerShell, then install the R
dependencies:

```powershell
Rscript --version
Rscript .\r_plot_library\ggplot2_cases\setup.R
Rscript .\r_plot_library\setup_animations.R
```

If PowerShell blocks virtual-environment activation or an R package fails to
install, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Model configuration

Open `.env` and configure one provider. Keep the other provider entries absent
or commented out.

Gemini:

```env
PROVIDER=gemini
MODEL=gemini-flash-latest
GOOGLE_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
```

Claude through LiteLLM:

```env
PROVIDER=litellm
MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=PASTE_YOUR_ANTHROPIC_API_KEY_HERE
```

OpenAI through LiteLLM:

```env
PROVIDER=litellm
MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE
```

For Claude and OpenAI, `litellm` is the ADK adapter; the prefix in `MODEL`
selects the model provider.

## Run PlotWorks

Run ADK from the directory that contains `PlotWorks/`, not from inside the
project directory.

Linux, macOS, or WSL:

```bash
cd ..
source PlotWorks/.venv/bin/activate
adk web --port 8000
```

Windows PowerShell:

```powershell
Set-Location ..
.\PlotWorks\.venv\Scripts\Activate.ps1
adk web --port 8000
```

Open the address reported by ADK and select `PlotWorks`. For a terminal-only
session, replace `adk web --port 8000` with `adk run PlotWorks`.

## Use PlotWorks

1. Put source files in `PlotWorks/data/`.
2. Tell the supervisor which file to inspect and what you want to learn or
   visualize.
3. Review any proposed transformation or generated code.
4. Use the ADK confirmation control when PlotWorks asks to save transformed
   data, execute generated code, or change a persistent setting.
5. Collect the result from `PlotWorks/outputs/`.

Useful prompts include:

```text
Inspect data/demo_general.csv, summarize its columns and missing values, and
recommend two plots. Do not save anything yet.
```

```text
Create a polished scatter plot of yield_kg versus rainfall_mm, colored by
treatment. Save it as yield_vs_rainfall.png.
```

```text
Render case 06-raincloud from simulated data using the ggrateful
terrapin_station palette.
```

For an animation that requires reshaping data:

```text
Inspect data/FAOSTAT_data_en_12-8-2024.xls. Preview the transformation needed
for an animated scatter plot of area harvested versus yield over Year, colored
by Area and sized by area harvested. Do not alter the source. Ask for
confirmation before saving the transformed table, then create the GIF.
```

Templates for the cotton-seed example are available under
`examples/transformations/` and `examples/animations/`.

## Inputs and outputs

Use paths relative to `PlotWorks/` whenever possible. When running under WSL,
use WSL paths such as `/mnt/c/...`, not `C:\...` paths. External absolute input
paths are disabled unless `.env` contains:

```env
ALLOW_ABSOLUTE_DATA_PATHS=true
```

| Result | Default location |
|---|---|
| Transformed data and metadata | `outputs/data/transformed/` |
| Static plots | `outputs/plots/` |
| Animations | `outputs/animations/` |
| Analysis reports | `outputs/reports/` |
| Generated code and run metadata | `outputs/code/` |

Plot filenames cannot include directories. Transformation output names may use
safe relative subfolders under `outputs/data/transformed/`.

### BED files

PlotWorks recognizes BED files through BED12. It treats the first three columns
as `chrom`, `chromStart`, and `chromEnd`, and can summarize interval counts,
lengths, scores, strands, and inferred chromosome sizes.

## Agent workflow infographic

Add the PlotWorks agent-workflow infographic here when it is available:

```markdown
![PlotWorks agent workflow](docs/images/plotworks-agent-workflow.png)
```

The graphic should show the supervisor receiving the request, delegating work
to specialists, pausing for user confirmation before protected actions, and
returning the finished data, plot, animation, or report. That is the useful
peek behind the curtain; the reader does not need the construction diary.

## Project structure

```text
PlotWorks/
├── agent.py              # Supervisor definition
├── agents/               # Specialist definitions
├── tools/                # Data, plotting, review, and reporting tools
├── plot_styles/          # Python themes, palettes, and export settings
├── plot_manifests/       # Approved plot recipes and defaults
├── r_plot_library/       # Shared R styles, recipes, and setup scripts
├── examples/             # Example transformations and animations
├── data/                 # Source datasets
├── outputs/              # Generated data, figures, reports, and code
├── tests/                # Automated tests
├── requirements.txt      # Python dependencies
└── .env.example          # Configuration template
```

Keep source data in `data/`; PlotWorks keeps its handiwork in `outputs/`.

## Specialist agents

| Agent | Role |
|---|---|
| `DataIntakeAgent` | Locates and inspects datasets. |
| `EDAAgent` | Produces exploratory summaries. |
| `DataTransformationAgent` | Previews deterministic or generated transformations. |
| `VisualizationPlannerAgent` | Chooses the most suitable plotting route. |
| `VisualizationAgent` | Creates deterministic Python plots. |
| `ColumnDecoderAgent` | Maps real column names to expected plotting roles. |
| `PublicationPlotAgent` | Renders approved ggplot2 recipes and manages palette proposals. |
| `RPlotDeveloperAgent` | Proposes custom static R plots. |
| `AnimationDeveloperAgent` | Produces standard or custom animations. |
| `PlotReviewAgent` | Checks raster dimensions, validity, and likely blankness. |
| `CodePlanningAgent` | Drafts non-executed Python or R plans. |
| `ReportAgent` | Creates Markdown reports. |
| `MethodResearchAgent` | Researches plotting methods when requested. |

For setup and runtime problems, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
