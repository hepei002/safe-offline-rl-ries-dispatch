# Applied Energy LaTeX manuscript package

This folder contains the LaTeX manuscript source for the safe offline RL study.

## Files

- `main.tex` — Elsevier `elsarticle` manuscript source for Applied Energy.
- `references.bib` — BibTeX library used by the manuscript.
- `tables/*.tex` — editable main-text tables generated from local CSV outputs.
- `../../results/figures/**` — figure files referenced by `main.tex`.

## Regenerate tables

From the project root:

```powershell
python scripts\generate_week20_latex_tables.py
```

## Compile

Preferred command, if a TeX distribution with `elsarticle` is installed:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

## Known remaining work

1. Replace placeholder authors and affiliations.
2. Insert the final repository DOI/accession.
3. Confirm funding, competing-interest and CRediT statements.
4. Confirm data-licence wording before public release.
