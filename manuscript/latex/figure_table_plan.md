# Figure and table plan for the Applied Energy LaTeX manuscript

## Figure contract

The main visual argument is:

> Offline RL becomes unsafe under predefined electricity--heat distribution shifts, and OOD-aware physical correction restores hard-safety reliability with measurable intervention and computation costs.

| Figure | Core conclusion | Evidence role | Export status |
|---|---|---|---|
| Fig. 1 | OOD risk is operationalized as adaptive action correction | Method schematic | PDF/PNG/SVG/TIFF exist |
| Fig. 2 | The scaled public-data system has seasonal load and renewable structure | Case-study context | PDF/PNG/SVG/TIFF exist |
| Fig. 3 | Deterministic dispatch is physically meaningful across typical days | Model validation | PDF/PNG/SVG/TIFF exist |
| Fig. 4 | Raw offline RL is unsafe under shifts; adaptive safety removes hard violations | Main result | PDF/PNG/SVG/TIFF exist |
| Fig. 5 | The safety gain is robust to method choices and sensitivity settings | Ablation | PDF/PNG/SVG/TIFF exist |
| Fig. 6 | Stress tests reveal robustness boundaries | Generalization | PDF/PNG/SVG/TIFF exist |
| Fig. 7 | Intervention rises when the system is risky | Mechanism/time-series | PDF/PNG/SVG/TIFF exist |
| Fig. 8 | Confidence intervals, tail risk and failure modes support the claims | Statistical close | PDF/PNG/SVG/TIFF exist |

## Table contract

| Table | Core conclusion | Source |
|---|---|---|
| Table 1 | The benchmark is a medium-sized electricity--heat industrial park | `docs/system_parameter_table.md` |
| Table 2 | Shifts are predefined, interpretable and grouped by mechanism | `results/shift_protocol_ood/shift_protocol_summary.csv` |
| Table 3 | Safety layer changes the cost--safety profile across scenarios | `results/week13_14_experiments/week13_main_summary.csv` |
| Table 4 | Adaptive safety significantly reduces hard safety cost in five-seed shifted scenarios | `results/week15_16_experiments/week16_pairwise_tests.csv` |
| Table 5 | Each main figure has a unique evidence role | local figure inventory |

## Review risks

- Do not treat single-seed stress tests as statistical evidence.
- Do not claim universal safety; the guarantee is limited to the modeled constraints and predefined shifts.
- Do not imply that the simulated park is a measured real site.
- Do not claim faster-than-MPC safety control without equalized solver and implementation benchmarking.

