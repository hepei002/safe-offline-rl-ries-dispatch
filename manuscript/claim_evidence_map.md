# Claim-evidence map

This file records the evidence used in `manuscript/applied_energy_safe_offline_rl_draft.md`. It is intentionally conservative: claims requiring final literature verification are marked as citation placeholders.

| Manuscript claim | Evidence source | Status |
|---|---|---|
| The study addresses a regional integrated electricity-heat system with grid exchange, wind, PV, CHP, heat pump, battery and thermal storage. | `docs/system_parameter_table.md`; `configs/system.yaml` | Supported |
| The benchmark system is a simulated medium-sized industrial park scaled to 10 MW electric peak and 18 MWth heat peak. | `docs/system_parameter_table.md` | Supported |
| Public exogenous time series from OPSD, When2Heat and OPSD Weather Data are aligned to a complete 2017-2019 hourly UTC table. | `docs/data_provenance.md`; `data/processed/exogenous/germany_joint_hourly_2017_2019.csv` | Supported |
| Offline trajectories are generated from physical simulation and behavior policies, not directly observed dispatch records. | `docs/offline_dataset_card.md`; `results/week5_behavior_policies/` | Supported |
| Distribution-shift protocol covers load, renewable, weather/COP, equipment and compound shifts. | `docs/shift_and_ood_protocol.md`; `configs/shift_protocol.yaml`; `results/shift_protocol_ood/shift_protocol_summary.csv` | Supported |
| Dynamics-ensemble OOD risk shows usable but imperfect safety-risk discrimination. | `docs/shift_and_ood_protocol.md`; `results/shift_protocol_ood/ood_risk_summary.csv` | Supported |
| Unprotected CQL and IQL incur hard safety cost under cold-wave, load-up and compound shifts. | `results/week13_14_experiments/week13_main_summary.csv`; `docs/week13_main_baselines.md` | Supported |
| Adaptive safety reduces hard safety cost to approximately zero in the 5-seed main scenarios. | `results/week13_14_experiments/week13_main_summary.csv`; `results/week15_16_experiments/week16_confidence_intervals.csv` | Supported |
| Paired tests show significant hard-safety reductions for adaptive CQL/IQL in cold-wave, compound and load-up scenarios. | `results/week15_16_experiments/week16_pairwise_tests.csv` | Supported |
| Adaptive safety has higher per-step computation time than raw offline RL but remains faster than full online optimization in the current implementation only when compared against the measured scripts cautiously. | `results/week13_14_experiments/week13_efficiency_table.csv`; `results/week13_14_experiments/week13_main_summary.csv` | Supported with boundary |
| Single-seed Week 15 stress scenarios are boundary/generalization evidence rather than inferential statistics. | `docs/week16_statistics_freeze.md`; `results/week15_16_experiments/week16_pairwise_tests.csv` | Supported |
| Related-work statements on MPC, offline RL, CQL, IQL, safe RL and energy systems require final verified references before submission. | `docs/research_question.md`, section 12; literature matrix still to be finalized | Needs citation verification |

