# Submission readiness checklist

This checklist is based on the current Applied Energy author-guide constraints checked on 2026-06-30. The official guide should be rechecked before final submission: <https://www.elsevier.com/journals/applied-energy/0306-2619/guide-for-authors>.

| Item | Current status | Action before submission |
|---|---|---|
| Full article draft | LaTeX manuscript prepared | Replace author, affiliation, funding and CRediT placeholders |
| Abstract length | Main LaTeX abstract within 250 words | Recheck after final edits |
| Highlights | Five bullets, all under 85 characters | Copy to separate submission field/file |
| Keywords | Present | Confirm 4-6 terms against journal preference |
| Figures | Manuscript-ready PDF/PNG/SVG exports generated | Prepare final upload package and graphical abstract |
| Tables | Compact LaTeX tables generated | Recheck formatting after final template compile |
| References | BibTeX library expanded and numeric style used | Final metadata/DOI spot-check before submission |
| Data availability | GitHub repository inserted | Add persistent release DOI/accession after archival |
| Generative AI declaration | Draft statement included | Align with Elsevier's current wording |
| Statistical reporting | CIs, paired tests and tail risk included | Avoid p-value claims for single-seed stress tests |
| Overclaim check | No obvious universal novelty/safety claims found | Re-run after literature and result edits |

## Revised abstract to use in the next manuscript sync

Offline reinforcement learning (offline RL) can train fast dispatch policies without unsafe online exploration, but policies trained from fixed datasets may fail when regional integrated energy systems experience distribution shifts in load, weather, renewable availability or equipment parameters. This paper develops a distribution-shift-aware safe offline RL framework for physics-constrained electricity-heat scheduling. The framework combines CQL or IQL policies with a dynamics-ensemble out-of-distribution (OOD) risk estimator and an adaptive safety layer that passes, partially corrects or fully projects policy actions toward the physical feasible set. A reproducible case study is built from public German electricity, heat and weather time series for 2017-2019 and scaled to a medium-sized industrial park with 10 MW electric peak load and 18 MWth heat peak load. The experiments compare perfect-information optimization, rolling MPC, rule-based dispatch, behavior cloning, TD3+BC, raw CQL/IQL, fixed safety projection and adaptive safety under in-distribution, load-increase, cold-wave, equipment-fault and compound-stress scenarios. Raw CQL and IQL are fast but unsafe under severe shifts: in the cold-wave extreme scenario, their mean hard safety costs reach 49.93 and 58.21, respectively. Coupling them with the adaptive safety layer reduces the corresponding mean hard safety cost below numerical tolerance across the five-seed main experiments, with significant paired reductions in cold-wave, compound and load-up scenarios. The results show that OOD-aware physical correction can make offline RL dispatch more reliable under predefined shifts, while exposing the computation and intervention costs required for this reliability.
