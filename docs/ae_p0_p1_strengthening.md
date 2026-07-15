# Applied Energy P0/P1 strengthening log

Date: 2026-07-15

## P0 submission-completeness items

| Item | Status | Notes |
|---|---|---|
| Public code/data repository | Done | GitHub repository: <https://github.com/hepei002/safe-offline-rl-ries-dispatch> |
| Persistent DOI/accession | Done | Zenodo DOI: <https://doi.org/10.5281/zenodo.21381039>. |
| Funding statement | Added | Zhejiang Provincial Excellent Funding for Postdoctoral Researchers (Grant No. ZJ2025156); China Postdoctoral Science Foundation (Grant No. 2025M784428). |
| CRediT statement | Draft added | Roles are drafted in `manuscript/latex/main.tex` and `manuscript/submission_materials_applied_energy.md`; all authors should confirm before submission. |
| Competing interests | Draft added | Current wording declares no known competing financial interests or personal relationships. Confirm with all authors. |
| Fig. 1 | Pending | User will redraw Fig. 1; final version should be vector PDF/SVG and replace the current manuscript figure. |

## P1 scientific-risk strengthening

### Fixed vs adaptive safety

The manuscript now clarifies that fixed projection and adaptive safety play different roles. Fixed projection restores modeled feasibility, whereas the adaptive layer uses OOD risk as a trust signal to determine how much of the learned action should be retained. The contribution is framed as reducing unnecessary correction and improving the cost--correction trade-off under the same feasibility target, rather than claiming that OOD risk alone guarantees safety.

### OOD risk interpretation

The manuscript now states that the dynamics-ensemble score is an imperfect but operationally useful trust indicator. The low AUPRC is not hidden; the discussion explains that the score should be interpreted together with AUROC, intervention rates and threshold ablations, and that the physical projection remains the actual feasibility-restoring mechanism.

### Relation to MPC

The manuscript avoids claiming that safe offline RL replaces MPC. The discussion frames the method as a hybrid learning-control architecture suitable for operator advisory, fallback triggering and stress-test diagnostics.

### Applied-energy positioning

A new discussion subsection, `Implications for resilient electricity--heat park operation`, connects cold waves, COP degradation, renewable shortfalls, equipment degradation and compound stress to practical electricity--heat park operation.

## Remaining before AE submission

- Verify the Zenodo DOI resolves and points to the intended archived release.
- Replace Fig. 1 with the final manually drawn vector figure.
- Confirm CRediT roles and competing-interest statement with all authors.
- Optionally add a figure-source-data map for all main figures.
