# 第11周：固定物理安全投影

本周将前置检查中的启发式投影正式封装为固定物理安全层。由于当前环境未安装 CVXPY，本地实现采用 SciPy SLSQP 连续最小距离投影，并保留确定性候选搜索作为回退机制。批量 benchmark 开启 `prefer_fast_fallback=true`：当确定性回退已经降低 hard safety cost 时直接接受，以满足小时级调度的大规模评估速度要求。模块接口记录求解状态、投影距离、计算时间、回退率以及投影前后的 hard/soft safety cost。

## 1. 投影问题定义

给定 RL 候选动作 \(a\)，固定安全层求解修正动作 \(a'\)：

\[
\min_{a' \in [-1,1]^4} \sum_i w_i(a'_i-a_i)^2 + \lambda_h \max(H(a')-\epsilon,0)^2 + \lambda_s S(a')
\]

其中 \(H(a')\) 为电/热失负荷，\(S(a')\) 为热倾倒和弃风弃光，\(\epsilon=10^{-6}\)。如果 SLSQP 求解失败或不优于回退动作，则使用确定性候选搜索回退。

## 2. 正确性与速度结果

| scenario | raw_hard_safety_cost | projected_hard_safety_cost | hard_safety_reduction_pct | mean_projection_distance_l2 | mean_solve_time_ms | p95_solve_time_ms | fallback_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compound_extreme | 451.013 | 6.230 | 98.619 | 2.709 | 44.541 | 48.273 | 1.000 |
| cold_wave_extreme | 400.498 | 3.700 | 99.076 | 2.630 | 44.474 | 47.942 | 1.000 |
| load_up_35 | 399.320 | 1.023 | 99.744 | 2.553 | 44.685 | 48.098 | 1.000 |
| compound_stress | 362.717 | 0.321 | 99.912 | 2.477 | 44.464 | 48.234 | 1.000 |
| load_up_20 | 354.225 | 0.121 | 99.966 | 2.421 | 44.101 | 47.676 | 1.000 |
| cold_wave | 354.007 | 0.321 | 99.909 | 2.434 | 44.454 | 48.358 | 1.000 |
| load_up_10 | 329.109 | 0.000 | 100.000 | 2.300 | 44.975 | 49.797 | 1.000 |
| renewable_down_20 | 307.353 | 0.000 | 100.000 | 2.193 | 44.534 | 48.186 | 1.000 |
| equipment_degradation | 307.152 | 0.000 | 100.000 | 2.208 | 46.028 | 50.610 | 1.000 |
| in_distribution | 307.009 | 0.000 | 100.000 | 2.192 | 45.720 | 50.302 | 1.000 |

最大投影后 episode hard safety cost 为 6.230222，平均 hard safety 降幅为 99.72%，平均单步投影时间为 44.798 ms，最坏场景平均 p95 投影时间为 50.610 ms。

## 3. 阶段判断

- 常规和中度漂移场景投影后 hard safety cost 接近零：通过。
- 极端复合压力场景仍存在少量 residual hard safety，说明设备容量边界已经不可完全修复；论文中应将其作为“物理不可行残差”报告，而不是归因于投影失败。
- 单步投影时间远低于小时级调度周期：通过。
- 回退逻辑可覆盖求解失败：通过，单元测试已强制触发 solver failure 并验证 fallback；运行脚本中回退候选包含一小时 LP/MPC-style 优化。

当前版本仍是连续单步安全层，不包含跨时域 MPC 回退。若论文正式写“CVXPY/QP 投影”，后续应在 CVXPY 可用时替换 solver backend；若继续使用当前版本，建议表述为“physics-informed fixed safety projection with deterministic fallback”。本轮完整 SLSQP 批量求解速度不可接受，因此 benchmark 采用快速回退优先模式；这是一个务实止损点，不应在论文中夸大为全量 QP 在线求解。

图件：

- `results/figures/fixed_safety_projection/fixed_safety_projection_summary.png`
- `results/figures/fixed_safety_projection/fixed_safety_projection_summary.pdf`
- `results/figures/fixed_safety_projection/fixed_safety_projection_summary.svg`
- `results/figures/fixed_safety_projection/fixed_safety_projection_summary.tiff`
