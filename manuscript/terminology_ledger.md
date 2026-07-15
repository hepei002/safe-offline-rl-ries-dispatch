# Terminology ledger for the Applied Energy manuscript draft

| Canonical term | First-use definition | Use rule |
|---|---|---|
| RIES | regional integrated energy system (RIES) | Use for the aggregated regional electricity-heat system studied in this manuscript. Do not imply a measured real industrial park. |
| Integrated electricity-heat system | regional integrated electricity-heat system | Use when spelling out the physical scope: grid exchange, wind, PV, CHP, heat pump, battery, thermal storage, electric load and heat load. |
| Offline RL | offline reinforcement learning (offline RL) | Use only for policies trained from fixed datasets without online exploration in the target energy system. |
| Distribution shift | distribution shift | Umbrella term for load, renewable, weather/COP, equipment and compound shifts. |
| OOD risk | out-of-distribution (OOD) risk | Risk score derived from state-action support and dynamics ensemble uncertainty. |
| Safety projection | physics-constrained safety projection | Minimum action-correction problem that maps a policy action toward the physical feasible set. |
| Adaptive safety layer | adaptive physics-constrained safety layer | OOD-risk-aware layer that chooses pass-through, partial projection or full projection. |
| Hard safety cost | hard safety cost | Scalar penalty for physical infeasibility, load shedding, SOC violations or residual hard constraint violations. |
| CVaR | conditional value-at-risk (CVaR) | Use for tail-risk summaries; specify the confidence level when reported. |
| CQL | conservative Q-learning (CQL) | Offline RL baseline and backbone policy. |
| IQL | implicit Q-learning (IQL) | Offline RL baseline and backbone policy. |
| MPC | model predictive control (MPC) | Rolling optimization baseline and possible fallback controller. |
| Perfect-information LP | perfect-information linear program | Deterministic benchmark with full horizon information; do not describe it as deployable real-time control. |
| Rule-based controller | rule-based controller | Deterministic heuristic dispatch baseline. |
| Fixed safety layer | fixed physics-constrained safety layer | Applies the projection rule without OOD-risk-dependent gating. |
| OOD warning | OOD warning | Diagnostic use of the OOD score without action correction. |

## Locked notation choices

- Use \(t\) for hourly time index.
- Use \(s_t\), \(a_t\), \(r_t\), \(c_t\) for state, action, reward and safety cost.
- Use \(R_{\mathrm{OOD}}\) for the OOD risk score.
- Use \(\Pi_{\mathcal{F}}\) for the safety projection onto the feasible set \(\mathcal{F}\).
- Use EUR for operating cost and MWh/MW/MWth/MWhth for energy-system units.

