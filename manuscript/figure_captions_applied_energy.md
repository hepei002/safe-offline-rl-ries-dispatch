# Figure captions for Applied Energy submission

These captions mirror the captions embedded in `manuscript/latex/main.tex` and are prepared as a separate editable figure-caption file if the submission system requests one.

## Figure 1. Method framework

OOD risk is used as an action-level trust signal rather than only as a diagnostic. The framework separates offline preparation, shifted deployment, dynamics-ensemble OOD estimation, adaptive gating, physics-constrained projection and evaluation outputs, clarifying that the learned policy proposes an action while the physical layer restores modeled feasibility when needed.

Source file: `results/figures/enhanced_manuscript/fig1_enhanced_framework.pdf`

## Figure 2. Annual input distributions

The public-data benchmark contains seasonal and tail operating conditions that make average-case dispatch insufficient. The annual distributions of scaled electricity load, heat load, renewable availability and weather-derived variables define the operating envelope used for distribution-shift testing.

Source file: `results/figures/system_profiles/annual_distribution.pdf`

## Figure 3. OOD-risk response

OOD risk rises under the shifts that are most relevant to physical safety, but it is not a safety certificate. The polar risk map, risk--unsafe-rate scatter and global AUROC/AUPRC panel show that the ensemble score is useful as an intervention signal while remaining imperfect for rare unsafe-transition classification.

Source file: `results/figures/enhanced_manuscript/fig3_enhanced_ood_polar.pdf`

## Figure 4. Main baseline comparison

Raw offline RL is computationally fast but unsafe under shifted conditions, whereas adaptive safety reduces hard-safety cost below numerical tolerance in the five-seed main scenarios. Violin and box plots show the distribution of safety and cost outcomes, while the heatmap and radar panel summarize intervention intensity and compound-stress trade-offs.

Source file: `results/figures/enhanced_manuscript/fig4_enhanced_main_violin.pdf`

## Figure 5. Ablation and sensitivity

The safety behavior is not explained by a single favourable dataset or parameter choice. Threshold curves, distance-weight bubbles, load-stress response, data-quality bubbles and safety-layer burden decomposition show how data support and correction design affect the cost--safety--conservatism trade-off.

Source file: `results/figures/enhanced_manuscript/fig5_enhanced_ablation_heatmap.pdf`

## Figure 6. Generalization and stress tests

Stress tests expose the boundary of the method rather than serving as independent statistical proof. The hard-safety heatmap, cost-ratio heatmap and polar intervention map show where unprotected offline RL can fail and where adaptive safety still restores modeled feasibility in recorded single-seed runs.

Source file: `results/figures/enhanced_manuscript/fig6_enhanced_stress_heatmap.pdf`

## Figure 7. Adaptive intervention trajectory

Adaptive intervention concentrates at the hours where the raw policy becomes least trustworthy. The trajectory links OOD risk, intervention decisions and hard-safety reduction in a representative stress episode, illustrating the mechanism behind the aggregate safety results.

Source file: `results/figures/week15_16/week15_intervention_trajectory.pdf`

## Figure 8. Statistical summary

Only the five-seed scenarios support inferential comparisons, while single-seed stress scenarios diagnose failure modes. The forest-style effect-size panel, paired-test evidence and tail-risk heatmap separate robust statistical evidence from boundary-screening evidence.

Source file: `results/figures/enhanced_manuscript/fig8_enhanced_statistics_forest.pdf`
