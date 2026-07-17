# Data Analysis Agency

**Data Analysis Agency** is a modular, provider-configurable Google ADK multi-agent app for exploratory data analysis. It is designed to help a user inspect a dataset, understand its structure, run basic exploratory statistics, create simple charts, generate analysis plans, and produce a plain-language report.

The app is intentionally organized like an agency: a **supervisor agent** plans the work and recruits specialist agents when their skills are useful for the user's request. This makes the workflow easier to maintain because model settings, search settings, prompts, tools, local data access, and agent orchestration are separated into different files.

---

## What this app does

The app can help with tasks such as:

- Listing available datasets in the project data folder
- Inspecting a dataset's shape, columns, data types, missing values, duplicates, and sample values
- Running deterministic exploratory data analysis with pandas
- Summarizing numeric and categorical variables
- Flagging possible data-quality issues
- Creating simple exploratory charts and saving them locally
- Writing a reproducible Python/pandas analysis plan
- Producing a user-facing Markdown report
- Optionally researching statistical methods or analysis conventions when web search is enabled

The most important design choice is that **statistics are calculated by Python tools, not invented by the language model**. The AI agents decide what to do, summarize results, and write reports, but pandas performs the actual computations.

---

## How the agency is organized

The root agent is the supervisor:

```text
DataAnalysisAgencySupervisor
```

The supervisor reads the user's request, forms a plan, and calls specialist agents as needed. It does not need to use every agent for every task.

### Specialist agents

| Agent | Main purpose | Typical use |
|---|---|---|
| `DataIntakeAgent` | Finds and inspects datasets | Use first when the user provides a dataset or asks what data is available |
| `EDAAgent` | Runs deterministic pandas-based EDA | Use for statistics, missingness, correlations, outliers, and summaries |
| `VisualizationAgent` | Creates simple charts | Use when the user asks for plots, charts, graphs, or visual EDA |
| `CodePlanningAgent` | Writes safe Python/pandas code plans | Use when the user asks for reproducible code or an analysis plan |
| `ReportAgent` | Writes final user-facing reports | Use when the user asks for a polished report or saved summary |
| `MethodResearchAgent` | Optional method research | Use only when external search is enabled and the user asks for methodological guidance |

---

## Recommended directory structure

Keep the project folder organized like this:

```text
Data_analysis_agency/
├── .venv/                         # local virtual environment; do not commit to GitHub
├── requirements.txt               # Python packages needed by the app
├── README.md                      # user guide for the app
└── data_analysis_agency/
    ├── __init__.py
    ├── agent.py                   # defines the supervisor/root agent
    ├── agent_cards.py             # short descriptions used by the supervisor to select agents
    ├── config.py                  # reads settings from .env
    ├── llm_factory.py             # switches between Gemini and LiteLLM-backed providers
    ├── prompts.py                 # instructions for supervisor and specialist agents
    ├── search_provider.py         # optional search-tool configuration
    ├── .env.example               # template for local settings
    ├── .env                       # your real local settings; do not commit to GitHub
    ├── agents/
    │   ├── __init__.py
    │   └── specialists.py         # creates the specialist agents
    ├── tools/
    │   ├── __init__.py
    │   ├── data_tools.py          # data loading, inspection, EDA, and chart tools
    │   └── report_tools.py        # Markdown report saving tool
    ├── data/                      # put datasets here
    └── outputs/                   # charts and reports are saved here
```

### Where to put datasets

Place datasets inside:

```text
data_analysis_agency/data/
```

For example:

```text
data_analysis_agency/data/soybean_traits.csv
data_analysis_agency/data/experiments/greenhouse_trial.xlsx
data_analysis_agency/data/example_project/phenotype_data.tsv
```

Relative file paths in your prompts are resolved from the `DATA_DIR` setting. For example, if the file is here:

```text
data_analysis_agency/data/experiments/greenhouse_trial.xlsx
```

You can prompt the app with:

```text
Analyze experiments/greenhouse_trial.xlsx. Inspect the format, run EDA, create basic charts, and write a report.
```

---

## Supported file types

The current data tools support:

```text
.csv
.tsv
.tab
.xlsx
.xls
.json
.txt
.data
```

Notes:

- CSV files are read with `pandas.read_csv()`.
- TSV and TAB files are read as tab-delimited files.
- Excel files use the first sheet by default unless the user specifies a sheet name.
- JSON files are read as standard JSON first, then as line-delimited JSON if needed.
- TXT and DATA files are treated as delimited text files and pandas attempts to infer the delimiter.

---

## Setup

From the folder that contains `data_analysis_agency/`, create and activate a virtual environment.

### Linux / WSL / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Then copy the environment template:

```bash
cp data_analysis_agency/.env.example data_analysis_agency/.env
```

On Windows PowerShell:

```powershell
Copy-Item data_analysis_agency/.env.example data_analysis_agency/.env
```

Then open `data_analysis_agency/.env` and add your model settings and API key.

---

## Important dependency note for LiteLLM users

If you use Claude, OpenAI, or another non-Gemini model through LiteLLM, make sure `orjson` is installed. A missing `orjson` package can cause an error like:

```text
ModuleNotFoundError: No module named 'orjson'
```

A good `requirements.txt` for this project is:

```text
google-adk
python-dotenv
pandas
numpy
matplotlib
openpyxl
litellm
orjson
```

If you already installed the project and then hit the `orjson` error, activate your virtual environment and run:

```bash
python -m pip install orjson
```

A more complete LiteLLM install is:

```bash
python -m pip install "litellm[proxy]"
```

For this app, installing `orjson` is usually enough to fix the immediate missing-dependency error.

---

## Environment settings

The app reads settings from:

```text
data_analysis_agency/.env
```

### Gemini example

Use this when running Gemini directly through ADK:

```env
PROVIDER=gemini
MODEL=gemini-flash-latest
GOOGLE_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE

DATA_DIR=./data_analysis_agency/data
OUTPUT_DIR=./data_analysis_agency/outputs
ALLOW_ABSOLUTE_DATA_PATHS=false
MAX_FILE_MB=100
MAX_PREVIEW_ROWS=8
ENABLE_WEB_SEARCH=false
```

### Claude through LiteLLM example

Use this when running Claude through ADK's LiteLLM adapter:

```env
PROVIDER=litellm
MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=PASTE_YOUR_ANTHROPIC_API_KEY_HERE

DATA_DIR=./data_analysis_agency/data
OUTPUT_DIR=./data_analysis_agency/outputs
ALLOW_ABSOLUTE_DATA_PATHS=false
MAX_FILE_MB=100
MAX_PREVIEW_ROWS=8
ENABLE_WEB_SEARCH=false
```

### OpenAI through LiteLLM example

```env
PROVIDER=litellm
MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE

DATA_DIR=./data_analysis_agency/data
OUTPUT_DIR=./data_analysis_agency/outputs
ALLOW_ABSOLUTE_DATA_PATHS=false
MAX_FILE_MB=100
MAX_PREVIEW_ROWS=8
ENABLE_WEB_SEARCH=false
```

### What the settings mean

| Setting | Meaning |
|---|---|
| `PROVIDER` | The model interface used by the app. Use `gemini` for native Gemini or `litellm` for providers routed through LiteLLM. |
| `MODEL` | The model name. For LiteLLM, include the provider prefix, such as `anthropic/...` or `openai/...`. |
| `GOOGLE_API_KEY` | API key for Gemini. |
| `ANTHROPIC_API_KEY` | API key for Claude models through LiteLLM. |
| `OPENAI_API_KEY` | API key for OpenAI models through LiteLLM. |
| `DATA_DIR` | Folder where the app looks for datasets. |
| `OUTPUT_DIR` | Folder where charts and reports are saved. |
| `ALLOW_ABSOLUTE_DATA_PATHS` | Whether the app can read files from absolute paths outside `DATA_DIR`. Default is safer: `false`. |
| `MAX_FILE_MB` | Maximum allowed input file size. |
| `MAX_PREVIEW_ROWS` | Number of sample values shown during data inspection. |
| `ENABLE_WEB_SEARCH` | Enables optional method research through search tools when supported. |

---

## Why `PROVIDER=litellm` for Claude?

In this app, `PROVIDER` means the **model interface** used by ADK.

For Gemini, ADK can use the model directly:

```text
ADK agent → Gemini
```

For Claude, this project uses LiteLLM as the bridge:

```text
ADK agent → LiteLLM adapter → Anthropic Claude
```

That is why Claude is configured like this:

```env
PROVIDER=litellm
MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=...
```

The true model provider is still Anthropic, but the app reaches it through the LiteLLM adapter.

---

## Running the app

From the folder that contains `data_analysis_agency/`, activate your virtual environment first.

### Terminal mode

```bash
adk run data_analysis_agency
```

### Browser mode

```bash
adk web --port 8000
```

Then open the local ADK web interface shown in your terminal.

---

## Example prompts

### Basic dataset inspection

```text
List the datasets available to analyze.
```

```text
Inspect soybean_traits.csv and summarize the columns, data types, missing values, duplicates, and sample values.
```

### Full exploratory analysis

```text
Analyze soybean_traits.csv. Inspect the format, run EDA, flag data-quality issues, create basic charts, and write a short final report.
```

### Excel file

```text
Analyze experiment_results.xlsx. Use the first sheet. Inspect the data, summarize numeric and categorical variables, and flag possible problems.
```

```text
Analyze experiment_results.xlsx using the sheet named Trial_1. Create basic charts and save a report.
```

### Nested data folder

```text
Analyze experiments/greenhouse_trial.xlsx. Run EDA, create charts, and summarize the most important findings.
```

### Code planning

```text
Write a reproducible Python analysis plan for phenotype.csv. Include loading, missingness checks, numeric summaries, categorical summaries, correlations, outlier checks, and plots.
```

### Report writing

```text
Run a full exploratory analysis on phenotype_data.tsv and save the final Markdown report.
```

### Method guidance

```text
I have a phenotype dataset with genotype groups and treatment groups. Suggest an analysis strategy before running EDA.
```

If `ENABLE_WEB_SEARCH=false`, the agency should rely on general model knowledge and local tools. If `ENABLE_WEB_SEARCH=true`, the `MethodResearchAgent` may use search for external method context.

---

## What output files to expect

The app saves generated files in:

```text
data_analysis_agency/outputs/
```

Possible outputs include:

```text
eda_trait_hist.png
eda_group_bar.png
20260716_214500_data_analysis_report.md
```

The exact filenames depend on the tool call and timestamp.

---

## Privacy and safety notes

This app is meant for local analysis support, but user prompts and tool outputs may still be sent to the selected model provider.

Recommended habits:

- Do not put API keys inside prompts.
- Do not upload or analyze sensitive personal data unless you are comfortable sending summaries to the model provider.
- Keep `.env` out of GitHub.
- Keep `.venv/`, `data/`, and `outputs/` out of GitHub if they contain private data or large files.
- Use relative paths inside `DATA_DIR` when possible.
- Keep `ALLOW_ABSOLUTE_DATA_PATHS=false` unless you specifically need broader local file access.

A useful `.gitignore` pattern is:

```gitignore
.venv/
__pycache__/
*.pyc
.env
data_analysis_agency/.env
data_analysis_agency/data/
data_analysis_agency/outputs/
```

---

## Common troubleshooting

### `ModuleNotFoundError: No module named 'orjson'`

Install the missing package inside the active virtual environment:

```bash
source .venv/bin/activate
python -m pip install orjson
```

Or install the fuller LiteLLM proxy extras:

```bash
python -m pip install "litellm[proxy]"
```

### The app cannot find my dataset

Check that the file is inside:

```text
data_analysis_agency/data/
```

Then refer to it by relative path:

```text
Analyze soybean_traits.csv.
```

If it is in a subfolder:

```text
Analyze experiments/soybean_traits.csv.
```

### The app says absolute paths are disabled

By default, the app only reads files inside `DATA_DIR`. This is safer. Either move the file into `data_analysis_agency/data/`, or change this setting in `.env`:

```env
ALLOW_ABSOLUTE_DATA_PATHS=true
```

Use that setting carefully.

### I changed `.env`, but the app still behaves the same

Stop and restart ADK:

```bash
Ctrl+C
adk web --port 8000
```

Environment settings are loaded when the app starts.

### I installed a package, but Python still cannot find it

Make sure your virtual environment is active:

```bash
which python
python -m pip list
```

The `python` path should point inside your project `.venv/` folder.

### LiteLLM provider errors

Check three things:

1. `PROVIDER=litellm`
2. `MODEL` includes the provider prefix, such as `anthropic/...` or `openai/...`
3. The matching API key exists in `.env`, such as `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

---

## How to extend the agency later

This project was designed so that you can add capabilities without rewriting everything.

### Add or edit agent instructions

Edit:

```text
data_analysis_agency/prompts.py
```

Use this when you want to change how an agent behaves.

### Add or edit specialist descriptions

Edit:

```text
data_analysis_agency/agent_cards.py
```

The supervisor uses these cards to decide which specialist to call.

### Add a new tool

Add or edit functions in:

```text
data_analysis_agency/tools/
```

Then attach the tool to a specialist agent in:

```text
data_analysis_agency/agents/specialists.py
```

### Add a new specialist agent

1. Add a new prompt in `prompts.py`.
2. Add a new description card in `agent_cards.py`.
3. Add a builder function in `agents/specialists.py`.
4. Add the new agent as an `AgentTool` in `agent.py` so the supervisor can recruit it.

### Switch model providers

Usually, you only need to edit:

```text
data_analysis_agency/.env
```

The model-routing logic is handled in:

```text
data_analysis_agency/llm_factory.py
```

---

## Current limitations

This starter app is intentionally simple. Current limitations include:

- It performs general EDA, not specialized statistical modeling.
- It creates basic charts only.
- It does not automatically clean or transform data unless future tools are added.
- It does not execute arbitrary user-written code.
- It does not automatically validate scientific assumptions.
- Very large datasets may need a more scalable loading strategy.
- Results depend on the quality and structure of the input data.

---

## Suggested first test

After setup, place one small CSV file in:

```text
data_analysis_agency/data/
```

Then run:

```bash
adk web --port 8000
```

Prompt:

```text
List available datasets, inspect my CSV file, run EDA, create basic charts, and save a short Markdown report.
```

This tests the full agency path: dataset discovery, intake, EDA, visualization, and reporting.
