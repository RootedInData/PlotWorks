# Data Analysis Agency

**Data Analysis Agency** is a modular Google ADK multi-agent workflow for local
data inspection, exploratory data analysis, polished Python plotting, approved
R/ggplot2 recipes, and experimental custom R plotting.

A supervisor reads the user's request, makes a plan, and recruits only the
specialists needed for that task. Deterministic tools calculate statistics,
load files, validate paths, render plots, and save outputs.

## Main capabilities

The agency can:

- Inspect CSV, TSV, Excel, JSON, text, DATA, BED, and BED.GZ files.
- Run deterministic pandas-based EDA.
- Summarize BED intervals, scores, strands, and inferred chromosome sizes.
- Map inconsistent column names to likely semantic roles.
- Create polished Python plots through reusable `pretty_*` functions.
- Render 20 approved ggplot2 plot recipes from simulated or supported real data.
- Write new plotting-only R code when the experimental feature is enabled.
- Validate generated R code before execution and save the code with the figure.
- Run technical checks for missing, invalid, or nearly blank raster plots.
- Save Markdown analysis reports.

## Plotting routes

The supervisor can choose among three plotting routes.

### 1. Approved R recipes

The predefined recipes under `r_plot_library/ggplot2_cases/` are the most
controlled route. Every recipe includes simulated data for preview and testing.
Some already accept a single compatible real-data table; others need additional
adapters for matrices, networks, hierarchies, or multiple linked tables.

Use this route for figures such as Manhattan plots, volcano-style plots,
raincloud plots, Sankey diagrams, treemaps, and the other cataloged cases.

### 2. Polished Python plots

Reusable Python functions use shared palettes, labels, legends, figure sizes,
and export settings:

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

These functions are deterministic and are preferred for routine plotting.
`create_basic_charts()` remains as a compatibility wrapper but now calls the
polished Python system internally.

### 3. Experimental custom R plotting

When no approved recipe fits and R offers a meaningful advantage, the
`RPlotDeveloperAgent` can write a new ggplot2 plotting function.

This feature is disabled by default. Enable it in `.env`:

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
The validator blocks package installation, system commands, network access,
file operations, directory changes, arbitrary `source()` calls, and unapproved
packages. Generated scripts and run metadata are saved under `outputs/code/`.

This is a conservative application-level guardrail, not a full operating-system
sandbox. Review generated code and figures before professional use.

## Project structure

```text
Data_analysis_agency/
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
│   ├── pretty_plot_tools.py
│   ├── visualization_planning_tools.py
│   ├── publication_plot_tools.py
│   ├── custom_r_plot_tools.py
│   ├── plot_review_tools.py
│   ├── r_bridge.py
│   └── report_tools.py
├── plot_styles/
│   ├── agency_publication.mplstyle
│   ├── palettes.py
│   ├── figure_presets.py
│   ├── labeling.py
│   └── accessibility.py
├── plot_manifests/
│   └── ggplot2_cases.json
├── r_plot_library/
│   ├── shared/
│   │   ├── theme_agency.R
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
├── data/
├── outputs/
│   ├── plots/
│   ├── reports/
│   └── code/
└── tests/
```

Keep user datasets in `data/`. Generated plots, reports, and generated R scripts
are kept in separate output subdirectories.

## Specialist agents

| Agent | Role |
|---|---|
| `DataIntakeAgent` | Locates and inspects datasets, including BED files. |
| `EDAAgent` | Runs deterministic exploratory statistics. |
| `VisualizationPlannerAgent` | Chooses approved R, `pretty_*` Python, or custom R. |
| `VisualizationAgent` | Calls deterministic polished Python plot functions. |
| `ColumnDecoderAgent` | Maps real column names to expected roles. |
| `PublicationPlotAgent` | Runs approved predefined ggplot2 recipes. |
| `RPlotDeveloperAgent` | Writes and executes guarded plotting-only R code. |
| `PlotReviewAgent` | Checks raster validity, dimensions, and likely blankness. |
| `CodePlanningAgent` | Writes non-executed Python or R plans. |
| `ReportAgent` | Produces and optionally saves a Markdown report. |
| `MethodResearchAgent` | Performs optional external method research. |

## Python setup

From the directory containing `Data_analysis_agency/`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r Data_analysis_agency/requirements.txt
cp Data_analysis_agency/.env.example Data_analysis_agency/.env
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r Data_analysis_agency\requirements.txt
copy Data_analysis_agency\.env.example Data_analysis_agency\.env
```

`orjson` is included because current LiteLLM code paths may import it before a
model request reaches Anthropic or OpenAI.

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

R plotting requires `Rscript` and the relevant packages in the same WSL/Linux
or operating-system environment where ADK runs.

```bash
Rscript --version
```

### Recommended WSL/Linux dependency route

The most reliable setup for difficult network and spatial dependencies is to
install available Ubuntu binaries first:

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
  r-cran-treemapify
do
  if apt-cache show "$pkg" >/dev/null 2>&1; then
    sudo apt install -y "$pkg"
  fi
done
```

Then run:

```bash
cd Data_analysis_agency/r_plot_library/ggplot2_cases
Rscript setup.R
```

### Personal R library

If the system library is not writable:

```bash
mkdir -p ~/R/data_analysis_agency_library
echo 'R_LIBS_USER=~/R/data_analysis_agency_library' >> ~/.Renviron
export R_LIBS_USER=~/R/data_analysis_agency_library
```

### Updating `ggraph` for a newer `ggplot2`

An Ubuntu `ggraph` can be older than a user-installed `ggplot2`. A guide-system
error in the module-network case can be corrected by installing current
`ggraph` into the user library:

```bash
export R_LIBS_USER=~/R/data_analysis_agency_library

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

Verify active versions and locations:

```bash
Rscript -e '
pkgs <- c("ggplot2","ggraph","igraph","tidygraph","graphlayouts")
for (pkg in pkgs) {
  cat(pkg, as.character(packageVersion(pkg)), find.package(pkg), "\n")
}
'
```

## Running the agency

Run ADK from the parent directory containing the agency folder:

```bash
adk run Data_analysis_agency
```

For the browser interface:

```bash
adk web --port 8000
```

If the parent directory contains multiple ADK apps, select
`Data_analysis_agency` in the web interface.

## Path guidance

The safest option is to place inputs in:

```text
Data_analysis_agency/data/
```

If ADK runs in WSL, use WSL-readable paths such as `/mnt/c/...`, not Windows
paths such as `C:\...`.

Absolute data paths are disabled by default:

```env
ALLOW_ABSOLUTE_DATA_PATHS=false
```

Set the value to `true` only when required.

Output parameters for plotting tools accept **filenames only**, not directory
paths. Use:

```text
my_plot.png
```

not:

```text
outputs/plots/my_plot.png
```

This prevents accidental nested paths such as
`outputs/plots/outputs/plots/`.

## BED support

The first three BED columns are interpreted as:

```text
chrom
chromStart
chromEnd
```

Optional BED fields are recognized through BED12. The agency can summarize
interval counts, lengths, scores, strands, and inferred chromosome sizes.

When true genome sizes are unavailable, the maximum `chromEnd` can be used as
an inferred size. The agency reports that this may underestimate chromosomes
when intervals do not reach their ends.

## Approved ggplot2 recipe behavior

Every approved case can represent real data in principle. The manifest uses:

- `direct_real_data_adapter_implemented`
- `real_data_adapter_pending`

A pending adapter generally means the recipe needs multiple linked tables, a
matrix, hierarchy metadata, or a graph object rather than one ordinary table.
It does not mean the plot type is inherently simulated-data-only.

To render all simulated previews, the agent should call the single deterministic
batch tool rather than making 20 separate calls:

```text
Render all approved ggplot2 cases from simulated data and summarize successes
and failures.
```

## Plot validation

`review_plot_file()` checks:

- File existence and size
- Image dimensions
- Basic image readability
- Extremely low pixel variation that may indicate a blank output
- Extreme aspect ratios

It does not verify scientific correctness, label accuracy, statistical honesty,
or subjective aesthetics. Human review remains necessary.

## Example prompts

### Inspect and analyze

```text
Inspect phenotype_data.csv, run EDA, and report data-quality issues.
```

### Choose a plotting route

```text
Inspect survey_results.csv and recommend whether an approved R recipe, a
pretty_* Python plot, or a custom R plot best fits my request to compare outcome
distributions across regions.
```

### Polished Python

```text
Create a pretty scatter plot of height versus biomass, color by treatment, add
a trend line, and save it as biomass_scatter.png.
```

```text
Create a pretty violin plot of yield by location and save it as yield_violin.png.
```

### Approved R recipe

```text
Create a publication-style Manhattan plot from gwas_results.csv.
```

```text
Render all approved ggplot2 cases from simulated data.
```

### Experimental custom R

```text
No approved recipe fits this dataset. Design a custom ggplot2 figure showing
monthly values by region with uncertainty ribbons. Use the shared agency theme,
validate the generated R code, execute it, and technically review the saved PNG.
```

## Troubleshooting

### No agents appear in ADK Web

Run `adk web` from the parent folder containing the agent app. Confirm that the
agency folder directly contains `agent.py` and `__init__.py`.

### `No module named 'orjson'`

```bash
source .venv/bin/activate
python -m pip install orjson
```

### `Rscript was not found on PATH`

Install R in the environment where ADK runs and verify:

```bash
Rscript --version
```

### An approved R plot fails

Run a full package check through the agency or inspect versions manually. Mixed
user-library and Ubuntu-library versions can cause extension incompatibilities.

### A custom R plot is rejected

The generated code must define `build_plot(data)` and use only allowed plotting
packages. It cannot load data, save files, install packages, access the network,
change directories, or call system/file-management functions.

### A plot is blank

Use `review_plot_file()` and inspect the R/Python error log. The renderer now
uses isolated run directories and removes invalid partial outputs rather than
reporting stale files as successful plots.

## Safety and privacy

- Keep API keys in `.env`.
- Keep sensitive inputs local unless intentionally shared with a model provider.
- Statistics come from deterministic tools rather than model invention.
- Approved R recipes use controlled arguments.
- Custom R code is plotting-only, validated, time-limited, and disabled by default.
- Review all generated code, plots, and reports before publication or decisions.

## Third-party plotting component

The R recipes under `r_plot_library/ggplot2_cases/` are adapted from
`ggplot2-20-journal-cases` and retained under its MIT License. The corresponding
license is located at:

```text
r_plot_library/ggplot2_cases/LICENSE
```

The surrounding ADK orchestration, data tools, column decoding, Python plotting
system, custom R validation/execution, and report workflow are agency-specific.
