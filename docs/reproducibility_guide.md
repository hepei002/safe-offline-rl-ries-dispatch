# Reproducibility guide

This guide records the intended public-repository workflow for reproducing the simulation benchmark, experiments and manuscript figures.

## 1. Environment

Recommended baseline:

- Python 3.10 or newer
- A TeX distribution with `pdflatex`, `bibtex` and `elsarticle`
- Optional Node.js only for regenerating earlier spreadsheet artifacts in `outputs/`, which are not required for the main manuscript workflow

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest tests
```

## 2. Data inputs

The GitHub repository should not include the large third-party raw CSV/ZIP files. Download the following versions and place them under `data/raw/`:

| Source | Local folder | Version used in this project | Purpose |
|---|---|---|---|
| OPSD Time Series | `data/raw/opsd/` | 2020-10-06 | German electricity load, renewable generation and related electricity-system time series |
| OPSD Weather Data | `data/raw/opsd_weather/` | 2020-09-16 | Weather context including temperature and radiation variables |
| When2Heat | `data/raw/when2heat/` | 2023-07-27 | Heat demand and heat-pump COP time series |

The exact provenance and licence notes are maintained in `docs/data_provenance.md` and `docs/data_availability_license_audit.md`.

## 3. Processed benchmark

The main processed benchmark is:

```text
data/processed/exogenous/germany_joint_hourly_2017_2019.csv
```

It uses a complete UTC hourly index from 2017-01-01 00:00:00 to 2019-12-31 23:00:00. The preprocessing workflow aligns timestamps to UTC, handles daylight-saving changes through UTC conversion, removes duplicate timestamps and records missing-value treatment in:

```text
data/processed/metadata/quality_report_2017_2019.json
```

Regenerate it from raw data:

```powershell
python src\data\build_joint_dataset.py
```

## 4. Experiment workflow

Run scripts in this order for a full refresh:

```powershell
python scripts\plot_system_profiles.py
python scripts\run_deterministic_dispatch.py
python scripts\generate_offline_dataset.py
python scripts\run_offline_rl_baselines.py
python scripts\run_shift_protocol_ood.py
python scripts\run_fixed_safety_projection.py
python scripts\run_adaptive_safety_mechanism.py
python scripts\run_week13_14_experiments.py
python scripts\run_week15_16_experiments.py
python scripts\generate_week20_latex_tables.py
python scripts\make_enhanced_manuscript_figures.py
```

The manuscript tables are generated from CSV summaries under `results/`. The manuscript figures are generated under `results/figures/`; TIFF exports are excluded from Git to avoid oversized repository history, while PDF/PNG/SVG versions can be retained for review and compilation.

## 5. Manuscript compilation

From `manuscript/latex/`:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The final public release should include the LaTeX source, BibTeX file, editable tables and figure source data or generation scripts.

## 6. Release checklist before journal submission

- Replace author, affiliation and funding placeholders in the manuscript.
- Archive the exact code/data release and insert the DOI/accession in the manuscript.
- Confirm third-party data attribution and licence wording.
- Tag the GitHub release with a stable version, for example `v1.0.0-submission`.
- Attach a compiled PDF only to the release page if desired; do not track build products in the main branch.

