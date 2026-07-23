# ggplot2-20-journal-cases

Twenty figure types that show up again and again in top-journal papers, rebuilt
from scratch in R with ggplot2. Each one runs on simulated data, so the whole
repository works on a fresh clone with nothing to download.

![Gallery of the 20 cases](assets/gallery.png)

## What this is

Every case is a small self-contained recipe: a `simulate.R` that generates the
data in base R, and a `plot.R` that builds and saves the figure. There are no
data files. The data is generated from a fixed seed each time, so a re-run gives
the same figure, and swapping in your own data is a matter of matching the
column names the simulator returns.

The figures mirror the structure of published examples (Manhattan and volcano
plots, Circos diagrams, Sankey flows, raincloud and split-violin plots,
treemaps, correlation and Mantel heatmaps, and more). All data here is
simulated; none of it is real or downloaded.

## Quick start

```bash
# 1. install the packages (once)
Rscript setup.R

# 2. render everything
Rscript scripts/run_all.R

# or render a single case
Rscript -e 'source("cases/04-manhattan-twas/plot.R")'
```

Run the scripts from the repository root. Paths are relative, so `plot.R` finds
`R/theme_case.R` and its own `simulate.R` without any setup.

`scripts/run_all.R` runs each case in its own R process and prints a pass/fail
table, so a broken simulator or plot shows up immediately.

## The 20 cases

| # | Figure type | Based on a figure from |
|---|-------------|------------------------|
| 01 | Individualized error dot-plot | Nature Microbiology |
| 02 | Grouped error dot-plot | Nature Cell Biology |
| 03 | Multi-group volcano | Nature Communications |
| 04 | Manhattan (TWAS) | iMeta |
| 05 | Paired boxplot | Nature Microbiology |
| 06 | Raincloud | Nature Communications |
| 07 | Swimmer plot | Nature |
| 08 | Importance bars + abundance streams | Nature Communications |
| 09 | Grouped variance bars with letters | Int. J. Mol. Sci. |
| 10 | Circos fusion-gene | Nature Communications |
| 11 | Module interaction network | Nature Communications |
| 12 | Sankey with an enrichment bubble panel | Nature Communications |
| 13 | Discrete (binned) heatmap | Nature Microbiology |
| 14 | Mantel composite heatmap | Nature Microbiology |
| 15 | Multi-group correlation heatmap | Nature Communications |
| 16 | Polar-coordinate heatmap | Nature Communications |
| 17 | Multi-level Sankey | Nature Communications |
| 18 | Treemap | Nature Communications |
| 19 | Mosaic and sunburst | Nature Communications |
| 20 | Split violin | Nature Communications |

## Layout

```
ggplot2-20-journal-cases/
├── README.md
├── setup.R                   # install every required package
├── R/theme_case.R            # shared theme, palettes, saver
├── scripts/run_all.R         # render every case, one process each
└── cases/
    ├── 01-error-dotplot/     # simulate.R, plot.R, figures/
    ├── ...
    └── 20-split-violin/
```

## Packages

Core: ggplot2, dplyr, tidyr, ggrepel, patchwork. By case: ggalluvial (Sankey),
treemapify (treemap), circlize (Circos), gghalves (raincloud and split violin),
ggh4x (per-panel strips), igraph and ggraph (network). `setup.R` installs all of
them, including the archived build of gghalves.

## License

[MIT](LICENSE). The code is original and the figures are independent rebuilds
from simulated data.
