# PlotWorks troubleshooting

This guide covers common setup and runtime problems. Start with the symptom
that matches what you see; there is no prize for reading error messages in
chronological order.

## `python`, `py`, or `adk` is not found

Activate the PlotWorks virtual environment before running ADK.

Linux, macOS, or WSL:

```bash
source PlotWorks/.venv/bin/activate
which python
which adk
```

Windows PowerShell:

```powershell
.\PlotWorks\.venv\Scripts\Activate.ps1
Get-Command python
Get-Command adk
```

Both commands should resolve inside `PlotWorks/.venv/`. If `adk` is still
missing, reinstall the pinned dependencies:

```bash
python -m pip install -r PlotWorks/requirements.txt
```

## PowerShell blocks virtual-environment activation

If `Activate.ps1` is blocked by the execution policy, allow locally created
scripts for your user account, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\PlotWorks\.venv\Scripts\Activate.ps1
```

If your computer is managed and the policy cannot be changed, run the virtual
environment's executables directly, for example:

```powershell
.\PlotWorks\.venv\Scripts\python.exe -m pip install -r .\PlotWorks\requirements.txt
.\PlotWorks\.venv\Scripts\adk.exe web --port 8000
```

## PlotWorks is missing from ADK Web

Start ADK from the directory containing the `PlotWorks/` folder:

```bash
adk web --port 8000
```

Do not start it from inside `PlotWorks/`. If several apps appear, select
`PlotWorks`.

## The model reports an API-key or provider error

Check that `PlotWorks/.env` exists and that `PROVIDER`, `MODEL`, and the matching
API-key variable are set. Do not mix a Gemini provider value with an OpenAI or
Anthropic model name. Restart ADK after editing `.env`.

## `Rscript` is not found

Install R and add its executable directory to your system path. Confirm from
the same terminal that runs ADK:

```bash
Rscript --version
```

On Windows, restart PowerShell after changing the system path. On WSL, install R
inside WSL; a Windows R installation is not automatically available there.

## An R package will not install

Run the supplied setup scripts again and keep the first error in the output:

```bash
cd PlotWorks
Rscript r_plot_library/ggplot2_cases/setup.R
Rscript r_plot_library/setup_animations.R
```

On Windows, some packages may require the Rtools release that matches your R
version. On Ubuntu or WSL, prefer distribution packages for difficult spatial
and animation dependencies when they are available.

If the R library is not writable on Linux or WSL, create a personal library:

```bash
mkdir -p ~/R/plotworks_library
echo 'R_LIBS_USER=~/R/plotworks_library' >> ~/.Renviron
export R_LIBS_USER=~/R/plotworks_library
```

Then rerun the setup scripts.

## A network or hierarchy plot is blank

An older `ggraph` can conflict with a newer `ggplot2`. Update `ggraph` in the R
library used by PlotWorks:

```bash
Rscript -e 'install.packages("ggraph", repos="https://cloud.r-project.org", dependencies=TRUE)'
```

Restart ADK after the update and render the plot again.

## An animation will not render

Run the animation setup script and confirm that FFmpeg is available for MP4
output:

```bash
Rscript PlotWorks/r_plot_library/setup_animations.R
ffmpeg -version
```

If FFmpeg is unavailable, install it through your operating system and restart
the terminal. GIF output may still work when MP4 output does not.

## A Windows path fails under WSL

Use a WSL path such as:

```text
/mnt/c/Users/your-name/path/to/file.csv
```

Do not pass `C:\Users\...` to an ADK process running inside WSL. The simplest
option is still to copy inputs into `PlotWorks/data/` and use relative paths.

## An external absolute path is rejected

Relative paths inside `PlotWorks/data/` are allowed by default. To allow other
absolute input paths, set this in `PlotWorks/.env` and restart ADK:

```env
ALLOW_ABSOLUTE_DATA_PATHS=true
```

Only enable it when PlotWorks should read data outside the project directory.

## The confirmation control does not appear

Use ADK Web for protected actions and confirm that the installed ADK version is
the version pinned in `requirements.txt`:

```bash
python -m pip show google-adk
```

Typed approval in chat does not replace the confirmation control. If a request
is waiting, check the web interface for a pending action. Restart ADK after any
environment or dependency change.

## A confirmed action reports success but no output appears

Check the expected directory under `PlotWorks/outputs/` and the ADK server log.
Record the request, returned tool payload, and first relevant error. Do not
overwrite the source file while investigating; PlotWorks outputs should remain
separate from inputs.

## A raster plot is missing or nearly blank

Confirm that the requested columns contain usable values after filtering and
that log-scaled values are positive. Check the ADK response for missing-column,
category-count, or plot-review warnings. If the plot uses a custom R route,
retry a deterministic Python plot or an approved R recipe to separate a data
problem from a custom-code problem.
