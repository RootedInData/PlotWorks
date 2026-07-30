# Tests

From the directory containing `PlotWorks/`, run:

```bash
python -m unittest discover -s PlotWorks/tests -v
```

The tests cover PlotWorks branding, polished Python plotting, managed output
filenames, deterministic and generated data transformation safeguards, custom
static R validation, and custom animation validation. R is not required for the
validation-only tests.
