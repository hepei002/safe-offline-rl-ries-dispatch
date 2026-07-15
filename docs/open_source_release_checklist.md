# GitHub open-source release checklist

## Repository hygiene

- [x] Confirm `.gitignore` excludes `data/raw/`, `data/interim/`, LaTeX build folders, Python caches, `node_modules/`, local Codex folders and large TIFF exports.
- [x] Confirm `.gitattributes` keeps source and documentation files as UTF-8 text.
- [x] Run `python -m pytest tests`.
- [ ] Rebuild manuscript figures and tables from scripts.
- [ ] Compile `manuscript/latex/main.tex` without undefined citations or references.
- [ ] Search for sensitive credentials before the first public push:

```powershell
rg -n "(?i)(api[_-]?key|secret|token|password|passwd|authorization|bearer|access_key|private_key)" . --glob "!docs/open_source_release_checklist.md"
```

## Data and licence

- [x] Do not commit third-party raw CSV/ZIP files.
- [x] Keep raw-data README/datapackage metadata when useful for provenance.
- [x] Keep `docs/data_provenance.md` and `docs/data_availability_license_audit.md` synchronized with the actual downloaded versions.
- [x] Release `data/processed/` and reproducibility files on GitHub: <https://github.com/hepei002/safe-offline-rl-ries-dispatch>.
- [x] Insert the archived release DOI/accession into `manuscript/latex/main.tex`: <https://doi.org/10.5281/zenodo.21381039>.
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
