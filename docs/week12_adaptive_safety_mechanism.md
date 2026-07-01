# 第12周：自适应安全机制

本周形成完整方法：OOD 风险估计不再单独作为最终目标，而是用于调节物理安全层的介入强度。方法由三部分组成：

1. dynamics ensemble OOD risk score；
2. fixed physical safety projection；
3. adaptive safety gate，将风险分数映射为 pass-through、partial projection 或 full projection。

## 1. 自适应规则

风险权重定义为：

\[
\rho = clip\left(\frac{r-r_l}{r_h-r_l},0,1\right)
\]

当风险低且动作本身无 hard safety violation 时，动作直接放行；当风险高时，使用固定安全投影；中间风险时，在原动作与固定安全动作之间搜索最近的可行混合动作，以减少过度修正。

## 2. 初步消融结果

| method | scenario | risk_score | projected_hard_safety_cost | hard_safety_reduction_pct | mean_projection_distance_l2 | intervention_rate | pass_through_rate | partial_projection_rate | full_projection_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adaptive_safety | cold_wave_extreme | 3.538 | 10.392 | 97.557 | 2.681 | 1.000 | 0.000 | 1.000 | 0.000 |
| adaptive_safety | compound_extreme | 3.625 | 15.922 | 96.577 | 2.745 | 1.000 | 0.000 | 1.000 | 0.000 |
| adaptive_safety | in_distribution | 3.032 | 0.000 | 100.000 | 2.050 | 1.000 | 0.000 | 1.000 | 0.000 |
| adaptive_safety | load_up_20 | 3.373 | 0.294 | 99.919 | 2.301 | 1.000 | 0.000 | 1.000 | 0.000 |
| fixed_safety | cold_wave_extreme | 3.538 | 10.392 | 97.557 | 2.723 | 1.000 | 0.000 | 0.000 | 1.000 |
| fixed_safety | compound_extreme | 3.625 | 15.922 | 96.654 | 2.747 | 1.000 | 0.000 | 0.000 | 1.000 |
| fixed_safety | in_distribution | 3.032 | 0.000 | 100.000 | 2.217 | 1.000 | 0.000 | 0.000 | 1.000 |
| fixed_safety | load_up_20 | 3.373 | 0.363 | 99.902 | 2.529 | 1.000 | 0.000 | 0.000 | 1.000 |
| no_safety | cold_wave_extreme | 3.538 | 314.722 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| no_safety | compound_extreme | 3.625 | 335.177 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| no_safety | in_distribution | 3.032 | 212.904 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| no_safety | load_up_20 | 3.373 | 253.631 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |

平均 projected hard safety cost：

- no safety：279.108
- fixed safety：6.669
- adaptive safety：6.652

平均动作修正距离：

- fixed safety：2.554
- adaptive safety：2.444

相对固定安全层，adaptive safety 的平均动作修正距离变化为 4.31%。

## 3. 阶段判断

自适应安全层相对 no safety 显著降低 hard safety risk；相对 fixed safety，在代表性压力动作设置下保持相近安全水平，并降低平均动作修正距离，但计算时间更高。这说明完整方法已经形成，且存在“降低过度修正”的初步证据。第 13 周完整基线实验中，应加入真实离线 RL 策略动作序列，进一步验证低风险时是否减少干预，并报告时间开销。

最终方法建议固定为：offline RL policy + ensemble risk score + adaptive physics-informed safety layer。不要再增加新核心模块。

图件：

- `results/figures/adaptive_safety/adaptive_safety_ablation.png`
- `results/figures/adaptive_safety/adaptive_safety_ablation.pdf`
- `results/figures/adaptive_safety/adaptive_safety_ablation.svg`
- `results/figures/adaptive_safety/adaptive_safety_ablation.tiff`
- `results/figures/adaptive_safety/adaptive_safety_method_flow.png`
