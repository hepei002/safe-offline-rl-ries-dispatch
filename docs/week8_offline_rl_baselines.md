# 第八周：离线强化学习基线与第一次止损判断

本周目标是跑通第一版普通离线强化学习基线，并完成 Go/No-Go 判断。由于当前环境没有安装 `d3rlpy`，本周采用项目内轻量 PyTorch 实现，覆盖 BC、TD3+BC、CQL 和 IQL 四类方法。该版本用于快速判断研究路线是否值得继续推进，不作为最终论文的充分训练版本。

## 1. 数据与算法

训练数据来自第七周生成的 Expert、Mixed 和 Poor 三类 Parquet transition 数据。状态、动作、奖励和下一状态均来自同一 Gymnasium 环境口径。

算法包括：

| 算法 | 当前实现 |
|---|---|
| BC | 行为克隆，最小化动作 MSE |
| TD3+BC | 双 Q critic + BC 正则 actor |
| CQL | 双 Q critic + 保守 Q 惩罚 + BC 正则 actor |
| IQL | expectile value + Q 回归 + advantage-weighted BC |

统一设置位于 `configs/offline_rl.yaml`：三随机种子、同一网络规模、同一训练步数、同一评估窗口和漂移协议。

## 2. 评估协议

分布内测试窗口从 2019-01-01 开始，按周间隔选取 12 个 24 h episode。漂移场景包括：

- `load_up`：电负荷和热负荷同时上升 15%。
- `price_spike`：购电价格参数放大 1.8 倍。
- `efficiency_drop`：热泵 COP 降低到 85%，CHP 燃气等效成本上升。

评价指标：

- 平均 episode 成本。
- CVaR90 episode 成本。
- 平均 episode safety cost。
- 平均 episode hard safety cost，即电/热失负荷。
- unsafe episode rate。
- 平均决策时间。

## 3. 输出文件

运行命令：

```powershell
python scripts\run_offline_rl_baselines.py
```

输出包括：

- `results/week8_offline_rl/offline_rl_seed_results.csv`
- `results/week8_offline_rl/offline_rl_learning_curves.csv`
- `results/week8_offline_rl/offline_rl_baseline_summary.csv`
- `results/week8_offline_rl/go_no_go.txt`
- `results/figures/offline_rl/learning_curves.png`
- `results/figures/offline_rl/seed_stability.png`
- `results/figures/offline_rl/id_vs_shift_comparison.png`

## 4. 当前版本注意事项

本周版本是“路线判断型”实验，有三点限制：

1. 训练步数较少，主要用于发现明显失败模式。
2. CQL/IQL 为轻量实现，后续正式实验建议替换为 d3rlpy 或 CORL 风格实现。
3. 评估场景数量有限，后续第 9–12 周会扩展到更系统的 OOD 风险估计和安全投影。

## 5. 本次快速实验结果

分布内测试结果如下。TD3+BC 是当前离线 RL 方法中表现最好的一个，显著优于 BC，但尚未超过规则控制器。

| 方法 | 分布内平均成本 € | CVaR90 成本 € | 平均 safety cost | 平均 hard safety cost | 平均决策时间 ms |
|---|---:|---:|---:|---:|---:|
| 规则控制 | 20824.01 | 27064.34 | 0.00 | 0.00 | 0.526 |
| TD3+BC | 49520.36 | 172213.40 | 106.12 | 3.07 | 0.401 |
| CQL | 121500.35 | 472518.95 | 69.89 | 12.33 | 0.311 |
| IQL | 154120.69 | 526663.99 | 64.61 | 16.42 | 0.308 |
| BC | 337635.67 | 930460.64 | 53.62 | 39.61 | 0.387 |

解释：

- TD3+BC 相比 BC 的分布内平均成本降低约 85%，说明至少一种普通离线 RL 方法能够明显优于 BC。
- 规则控制器仍显著强于当前轻量离线 RL，实现上必须作为强基线保留，不能只与 BC 比较。
- `safety_cost` 包含热倾倒、弃风弃光和失负荷等软/硬安全项；`hard safety cost` 只统计电/热失负荷，更适合判断真正不可供能风险。

## 6. 初步漂移结论

三类漂移中，负荷上升最明显地恶化普通离线 RL 的成本和硬安全风险。例如：

| 方法 | ID hard safety | 负荷上升 hard safety | 变化 |
|---|---:|---:|---:|
| BC | 39.61 | 64.68 | +63% |
| TD3+BC | 3.07 | 8.23 | +168% |
| CQL | 12.33 | 25.17 | +104% |
| IQL | 16.42 | 31.36 | +91% |

这支持论文主张中的关键前提：普通离线 RL 在合理分布漂移下会出现可测量退化。

## 7. Go/No-Go 判断

当前结论为：

> Conditional Go：普通离线 RL 已明显优于 BC，且漂移场景会显著恶化安全风险；但当前离线 RL 尚未超过规则控制器，因此继续推进 OOD 风险估计和安全机制时，必须把规则控制作为强基线，并在第 9–10 周同步改进离线 RL 训练设置。

后续建议：

1. 第 9 周继续做 OOD 风险估计，因为漂移退化已经存在。
2. 第 8–9 周之间可把 TD3+BC/IQL 训练步数提高，并尝试只用 Expert+Mixed 训练，减少 Poor 数据对策略的污染。
3. 第 13 周完整基线实验中必须纳入规则控制和 MPC，避免只与 BC 比较导致结论偏弱。
