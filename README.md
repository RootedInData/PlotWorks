# Data Analysis Agency

**Data Analysis Agency** is a modular Google ADK multi-agent workflow for local data inspection, exploratory data analysis, simple charts, and approved publication-style plots.

The agency uses a **supervisor agent** that reads the user request, decides what needs to happen, and recruits the right specialist agents. It is intentionally divided into separate agents, tools, prompts, model configuration, search configuration, local document access, and plotting modules so the system can grow without becoming one large tangled script.

---

## What the agency can do

The agency can:

- Find datasets in the local `data/` folder.
- Inspect common tabular data files.
- Recognize and summarize `.bed` genomic interval files.
- Run deterministic pandas-based EDA.
- Report missing values, column types, categorical summaries, numeric summaries, correlations, and outlier warnings.
- Create basic exploratory charts with Python.
- Create approved ggplot2 publication-style plots through R.
- Render demo publication-style plots from simulated data included with the approved plot cases.
- Write a clear final report and save it as Markdown.
- Write safe analysis/code plans for the user to review.

The agency does **not** run arbitrary user-provided R code for publication plots. Publication-style plots are limited to predefined, approved recipes.

---

## Recommended directory structure

Keep the project organized like this:

```text
Data_Analysis_Agency/
├── .env.example
├── .env                         # you create this from .env.example
├── README.md
├── requirements.txt
├── agent.py                     # supervisor/root agent
├── agent_cards.py               # descriptions the supervisor uses for routing
├── config.py                    # environment and path settings
├── llm_factory.py               # model/provider configuration
├── prompts.py                   # agent instructions
├── search_provider.py           # optional search setup
├── agents/
│   ├── __init__.py
│   └── specialists.py           # specialist agent builders
├── tools/
│   ├── __init__.py
│   ├── data_tools.py            # data loading, EDA, BED support, basic charts
│   ├── publication_plot_tools.py # approved publication plotting tools
│   ├── r_bridge.py              # Python-to-R bridge and path checks
│   └── report_tools.py          # report saving
├── plot_manifests/
│   └── ggplot2_cases.json       # approved plot recipe metadata
├── r_plot_library/
│   └── ggplot2_cases/           # copied R plotting cases
├── data/                        # put user datasets here
└── outputs/
    ├── plots/                   # generated plots
    └── reports/                 # generated reports
```

The safest practice is to place input datasets inside:

```text
Data_Analysis_Agency/data/
```

Generated files are saved under:

```text
Data_Analysis_Agency/outputs/plots/
Data_Analysis_Agency/outputs/reports/
```

---

## Specialist agents

The supervisor can recruit these agents as needed:

| Agent | Main job |
|---|---|
| `DataIntakeAgent` | Finds and inspects datasets, including BED files. |
| `EDAAgent` | Runs deterministic pandas-based EDA. |
| `VisualizationAgent` | Creates simple Python charts. |
| `ColumnDecoderAgent` | Matches real column names to expected plot recipe columns. |
| `PublicationPlotAgent` | Creates approved ggplot2 publication-style plots through R. |
| `CodePlanningAgent` | Writes safe reproducible analysis/code plans. |
| `ReportAgent` | Synthesizes results into a final report. |
| `MethodResearchAgent` | Optionally searches for method/package guidance when enabled. |

The supervisor does not need to use every agent for every task. For example, a request to inspect a BED file may only need `DataIntakeAgent`, while a request for a publication-style Manhattan plot may need `DataIntakeAgent`, `ColumnDecoderAgent`, and `PublicationPlotAgent`.

---

## Setup

### 1. Create and activate a Python environment

From the folder containing `Data_Analysis_Agency/`:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```bash
pip install -r Data_Analysis_Agency/requirements.txt
```

If you use Claude or OpenAI through LiteLLM, the `orjson` dependency is important. A missing `orjson` package can cause LiteLLM to fail before the model call reaches the provider.

### 3. Create your `.env` file

```bash
cp Data_Analysis_Agency/.env.example Data_Analysis_Agency/.env
```

Then edit `Data_Analysis_Agency/.env` and add your API key.

---

## Model provider configuration

### Gemini through ADK

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

Here, `PROVIDER=litellm` means the agency is using ADK's LiteLLM adapter. The actual model provider is identified inside the model name: `anthropic/...`.

### OpenAI through LiteLLM

```env
PROVIDER=litellm
MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE
```

---

## R setup for publication-style plots

Publication-style plots use copied R/ggplot2 case recipes under:

```text
Data_Analysis_Agency/r_plot_library/ggplot2_cases/
```

To use these plot recipes, the user's system must have:

1. R installed.
2. `Rscript` available on the command line.
3. The required R packages installed.

Check R:

```bash
Rscript --version
```

### Recommended WSL/Linux package setup

If you are using WSL or Linux, install the harder R plotting dependencies through Ubuntu's prebuilt `r-cran-*` packages first. This is the recommended route because packages such as `igraph`, `ggraph`, `sf`, and related dependencies may fail when R tries to compile them from source.

Run this from the Linux/WSL terminal:

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
    echo "Installing $pkg"
    sudo apt install -y "$pkg"
  else
    echo "Not available from apt: $pkg"
  fi
done
```

After that, run the project setup script from the ggplot2 case folder:

```bash
cd Data_Analysis_Agency/r_plot_library/ggplot2_cases
Rscript setup.R
```

The setup script can then fill remaining package gaps instead of trying to build every difficult dependency from source.

### Optional personal R library

If R tries to install packages into a system folder such as `/usr/local/lib/R/site-library` and reports that it is not writable, create a personal R package library:

```bash
mkdir -p ~/R/data_analysis_agency_library
echo 'R_LIBS_USER=~/R/data_analysis_agency_library' >> ~/.Renviron
export R_LIBS_USER=~/R/data_analysis_agency_library
```

Then rerun:

```bash
cd Data_Analysis_Agency/r_plot_library/ggplot2_cases
Rscript setup.R
```

The agency can still inspect data and run EDA while R plotting packages are being fixed.

---

## Path guidance

The agency includes checks to confirm paths can be read by both Python and R.

The simplest rule is:

> Use paths that are readable from the same environment where you run `adk run` or `adk web`.

If you run ADK from WSL, prefer WSL-style paths:

```text
/mnt/c/Users/yourname/path/to/file.csv
```

rather than Windows-style paths:

```text
C:\Users\yourname\path\to\file.csv
```

The safest option is to place files in:

```text
Data_Analysis_Agency/data/
```

Then refer to them by name:

```text
Analyze soybean_traits.csv
```

By default, absolute file paths are disabled for safety. To allow them, set this in `.env`:

```env
ALLOW_ABSOLUTE_DATA_PATHS=true
```

---

## Supported data files

The agency currently supports:

```text
.csv
.tsv
.tab
.xlsx
.xls
.json
.txt
.data
.bed
.bed.gz
```

---

## BED file support

BED files are common in bioinformatics and are handled as genomic interval data.

The agency expects the first three BED fields to be:

```text
chrom
chromStart
chromEnd
```

Optional BED fields are also recognized when present:

```text
name
score
strand
thickStart
thickEnd
itemRgb
blockCount
blockSizes
blockStarts
```

For BED files, the agency can summarize:

- Number of intervals.
- Number of chromosomes or scaffolds.
- Top chromosomes/scaffolds by interval count.
- Interval length summaries.
- Score summaries when a score column exists.
- Strand counts when strand information exists.
- Inferred chromosome/scaffold lengths from max `chromEnd`.

If a genome-wide plot needs chromosome sizes and you do not provide a genome sizes file, the agency can infer sizes from the largest `chromEnd` in the BED file. This is useful, but may underestimate true chromosome lengths if the BED file does not include intervals near chromosome ends.

---

## Column naming guidance

Real-world datasets often use different names for the same idea. The agency includes a `ColumnDecoderAgent` to recognize common variants.

Examples that should usually be recognized as similar:

```text
start
Start
chrom_start
chromStart
```

```text
chr
chrom
chromosome
CHR
```

```text
p
pvalue
p_value
p.val
P
```

However, clear standardized names are still best. When a plot recipe requires specific fields, use column names that clearly express the role of each column. If multiple columns could match the same role, the agency should report the uncertainty rather than silently guessing.

---

## Publication-style plotting

The agency includes approved ggplot2 cases in:

```text
Data_Analysis_Agency/r_plot_library/ggplot2_cases/
```

The recipe metadata lives in:

```text
Data_Analysis_Agency/plot_manifests/ggplot2_cases.json
```

The plot recipe names intentionally use `ggplot2_cases`, not `ggplot2_journal_cases`.

### Important rule

For publication-style plots, the agency only runs predefined recipes with controlled arguments. It does not run arbitrary user-provided R code.

### Demo plots from simulated data

Each copied ggplot2 case includes simulation code. The agency can render a demo plot from simulated data when the user asks for an example or preview.

Example prompt:

```text
Show me a demo of the Manhattan plot case.
```

Example prompt:

```text
Render a simulated split violin plot so I can see what the style looks like.
```

### Real-data publication plots

For real data, the agency checks whether your columns can be mapped to the required fields for the selected recipe. If the data does not support the requested plot, it should tell you what is missing.

Example prompt:

```text
Make a publication-style Manhattan plot from gwas_results.csv.
```

Example prompt:

```text
What ggplot2 publication-style plots can this dataset support?
```

Example prompt:

```text
Create a raincloud plot from phenotype_traits.csv and save it to outputs/plots.
```

Some plot cases are demo-only in this starter version because they require complex R objects, matrices, graphs, or multiple linked tables rather than one simple data frame.

---

## Running the agency

From the folder containing `Data_Analysis_Agency/`:

```bash
adk run Data_Analysis_Agency
```

Or use the browser UI:

```bash
adk web --port 8000
```

Then choose the `Data_Analysis_Agency` app in the ADK web interface.

---

## Example prompts

### Inspect a dataset

```text
Inspect soybean_traits.csv and tell me about the columns, missing values, and data types.
```

### Run EDA

```text
Run exploratory data analysis on phenotype_data.csv. Summarize missingness, numeric variables, categorical variables, correlations, and possible outliers.
```

### Analyze a BED file

```text
Inspect repeats.bed. Summarize the chromosomes, interval lengths, scores, strands, and inferred chromosome sizes.
```

### Basic charts

```text
Create basic exploratory charts for soybean_traits.csv.
```

### Publication-style plots

```text
List the approved ggplot2 publication-style plot cases.
```

```text
What publication-style plots can phenotype_data.csv support?
```

```text
Make a demo plot for case 04-manhattan-twas using simulated data.
```

```text
Make a publication-style Manhattan plot from gwas_results.csv.
```

### Reports

```text
Analyze soybean_traits.csv, create relevant charts, and save a Markdown report.
```

---

## Troubleshooting

### `No module named 'orjson'`

Install `orjson` in the same virtual environment:

```bash
source .venv/bin/activate
python -m pip install orjson
```

Or reinstall requirements:

```bash
python -m pip install -r Data_Analysis_Agency/requirements.txt
```

### `Rscript was not found on PATH`

Install R in the same environment where ADK is running, then check:

```bash
Rscript --version
```

### R packages are missing

For WSL/Linux, use the Ubuntu prebuilt package route first:

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
    echo "Installing $pkg"
    sudo apt install -y "$pkg"
  else
    echo "Not available from apt: $pkg"
  fi
done
```

Then rerun the project setup script:

```bash
cd Data_Analysis_Agency/r_plot_library/ggplot2_cases
Rscript setup.R
```

This route is often more reliable than asking R to compile large packages such as `igraph`, `sf`, `tidygraph`, and `ggraph` from source.

### R says the system library is not writable

If you see a message like this:

```text
'lib = "/usr/local/lib/R/site-library"' is not writable
```

create and use a personal R library:

```bash
mkdir -p ~/R/data_analysis_agency_library
echo 'R_LIBS_USER=~/R/data_analysis_agency_library' >> ~/.Renviron
export R_LIBS_USER=~/R/data_analysis_agency_library
```

Then rerun:

```bash
cd Data_Analysis_Agency/r_plot_library/ggplot2_cases
Rscript setup.R
```

### Some R packages still fail

The publication plot system allows partial case availability. This means the agency can still inspect data, run EDA, write reports, and generate any plots whose required packages are installed.

If the setup still fails, look for the **first package-specific error** in the log. The final lines often show downstream failures only. For example, if `igraph` fails, then `tidygraph` and `ggraph` may also fail because they depend on it.

### R cannot read my file path

Use a path readable from the ADK runtime environment. If using WSL, prefer `/mnt/c/...` paths or place the file inside the agency `data/` folder.

### My data does not support the plot I requested

The agency should tell you which required columns are missing. Rename columns to standardized terms or choose a plot recipe that matches your data.

For example, a Manhattan plot usually needs:

```text
CHR
BP
P
```

A BED file with only `chrom`, `chromStart`, and `chromEnd` can be summarized, but it cannot produce a p-value Manhattan plot unless p-values or an equivalent signal column are also provided.

---

## Suggested `.gitignore`

```gitignore
.env
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
Data_Analysis_Agency/data/*
Data_Analysis_Agency/outputs/*
!Data_Analysis_Agency/data/.gitkeep
!Data_Analysis_Agency/outputs/.gitkeep
```

---

## Safety and privacy notes

- Keep sensitive datasets local unless you intentionally choose otherwise.
- The model receives summaries and tool outputs, not necessarily the full raw dataset.
- Do not place API keys in source code.
- Publication-style R plotting is restricted to approved recipes and controlled arguments.
- Review all generated plots and reports before using them in a professional or publication context.
