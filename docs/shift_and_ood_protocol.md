# 分布漂移协议与 OOD 风险估计

本文档对应第 9 周任务：正式定义分布漂移协议，并实现 OOD 风险估计。协议配置见 `configs/shift_protocol.yaml`，结果文件位于 `results/shift_protocol_ood/`。

## 1. 分布漂移协议

协议名称：`applied_energy_shift_protocol_v1`。

参考分布使用 Expert 离线数据中的安全 transition；评估期从 `2019-01-01 00:00:00+00:00` 开始，按 24 小时 episode、168 小时间隔抽取 12 个 episode。评估控制器为 `rule_based`。

漂移场景覆盖四类机制：负荷上升、可再生出力下降、天气/COP 异常、设备退化，以及一个复合压力场景。

| scenario | family | mean_absolute_relative_change | electric_load_mw_relative_change | heat_load_mw_th_relative_change | pv_available_mw_relative_change | wind_available_mw_relative_change | cop_ashp_radiator_relative_change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| in_distribution | baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| load_up_10 | load | 0.033 | 0.100 | 0.100 | 0.000 | 0.000 | 0.000 |
| load_up_20 | load | 0.067 | 0.200 | 0.200 | 0.000 | 0.000 | 0.000 |
| renewable_down_20 | renewable | 0.049 | 0.000 | 0.000 | 0.091 | 0.200 | 0.000 |
| cold_wave | weather | 1.655 | 0.000 | 0.250 | 0.000 | 0.000 | 0.150 |
| equipment_degradation | equipment | 0.058 | 0.000 | 0.000 | 0.046 | 0.100 | 0.200 |
| compound_stress | compound | 1.136 | 0.150 | 0.250 | 0.114 | 0.200 | 0.150 |
| load_up_35 | load_extreme | 0.117 | 0.350 | 0.350 | 0.000 | 0.000 | 0.000 |
| cold_wave_extreme | weather_extreme | 2.507 | 0.000 | 0.500 | 0.000 | 0.000 | 0.250 |
| compound_extreme | compound_extreme | 2.662 | 0.300 | 0.600 | 0.183 | 0.350 | 0.250 |

## 2. OOD 风险估计方法

本次使用 dynamics ensemble risk estimator。每个模型输入 state-action，预测下一状态增量；OOD 分数由三部分组成。hard safety 风险标签定义为 `hard_safety_cost > 1e-6`，避免将数值求解残差误判为失负荷。

\[
R_{ood} = R_{disagreement} + R_{prediction\ error} + 0.05 R_{novelty}
\]

其中 `disagreement` 表示模型集成预测分歧，`prediction error` 表示平均模型的下一状态预测误差，`novelty` 表示 state-action 相对 Expert 安全样本的分布新颖度。最终用训练集 90 分位原始风险作尺度归一化。

## 3. 结果

全局 hard safety 风险识别结果：

- AUROC：0.708
- AUPRC：0.038
- Spearman：0.045
- unsafe transition rate：0.024

分场景结果：

| scenario | transitions | mean_ood_score | p90_ood_score | mean_hard_safety_cost | unsafe_rate | auroc | auprc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cold_wave | 288 | 3.266 | 4.419 | 0.013 | 0.014 | 0.658 | 0.024 |
| cold_wave_extreme | 288 | 3.538 | 5.177 | 0.154 | 0.073 | 0.655 | 0.098 |
| compound_extreme | 288 | 3.625 | 4.416 | 0.260 | 0.097 | 0.702 | 0.144 |
| compound_stress | 288 | 3.201 | 3.756 | 0.013 | 0.014 | 0.709 | 0.028 |
| equipment_degradation | 288 | 3.185 | 4.532 | 0.000 | 0.000 | 0.500 | 0.000 |
| in_distribution | 288 | 3.032 | 3.299 | 0.000 | 0.000 | 0.500 | 0.000 |
| load_up_10 | 288 | 3.184 | 3.293 | 0.000 | 0.000 | 0.500 | 0.000 |
| load_up_20 | 288 | 3.373 | 3.510 | 0.005 | 0.010 | 0.731 | 0.025 |
| load_up_35 | 288 | 3.707 | 3.672 | 0.043 | 0.035 | 0.668 | 0.052 |
| renewable_down_20 | 288 | 2.832 | 2.899 | 0.000 | 0.000 | 0.500 | 0.000 |

## 4. 阶段判断

若全局 AUROC 稳定高于 0.65，说明 ensemble OOD 分数已经具备继续进入安全约束/投影联动实验的价值；若低于 0.65，则 OOD 模块仍只能作为辅助诊断，不宜作为论文主创新点。

本轮图件：

- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.png`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.pdf`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.svg`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.tiff`
