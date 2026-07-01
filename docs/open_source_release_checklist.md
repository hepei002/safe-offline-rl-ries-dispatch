# GitHub open-source release checklist

## Repository hygiene

- [ ] Confirm `.gitignore` excludes `data/raw/`, `data/interim/`, LaTeX build folders, Python caches, `node_modules/`, local Codex folders and large TIFF exports.
- [ ] Confirm `.gitattributes` keeps source and documentation files as UTF-8 text.
- [ ] Run `python -m pytest tests`.
- [ ] Rebuild manuscript figures and tables from scripts.
- [ ] Compile `manuscript/latex/main.tex` without undefined citations or references.
- [ ] Search for sensitive credentials before the first public push:

```powershell
rg -n "(?i)(api[_-]?key|secret|token|password|passwd|authorization|bearer|access_key|private_key)" . --glob "!docs/open_source_release_checklist.md"
```

## Data and licence

- [ ] Do not commit third-party raw CSV/ZIP files.
- [ ] Keep raw-data README/datapackage metadata when useful for provenance.
- [ ] Keep `docs/data_provenance.md` and `docs/data_availability_license_audit.md` synchronized with the actual downloaded versions.
- [ ] Confirm whether `data/processed/` is released on GitHub, Zenodo/Figshare/Mendeley Data, or both.
- [ ] Insert the archived release DOI/accession into `manuscript/latex/main.tex`.
- [ ] Add a `CITATION.cff` file after the final author list and DOI/accession are fixed.

## Suggested first Git commands

If the folder is not yet a valid Git repository:

```powershell
git init
git add .gitignore .gitattributes README.md LICENSE requirements.txt configs docs manuscript scripts src tests data/README.md data/processed results
git status --short
```

Inspect the staged file list carefully before committing:

```powershell
git diff --cached --stat
```

Then commit:

```powershell
git commit -m "Prepare reproducible open-source research repository"
```

Do not run `git add .` until the ignored-file behavior has been checked.
