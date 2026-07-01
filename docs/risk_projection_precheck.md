# OOD 风险评分与物理安全投影前置检查

本文档对应止损判断后的三项补强工作：

1. 将 `safety_cost` 拆分为 hard safety 与 soft operation cost。
2. 验证简单 OOD 分数是否能预测 hard safety risk。
3. 实现一步物理安全投影，并检查其是否能降低 hard safety cost。

## 1. 安全成本拆分

已新增：

- `src/safety/costs.py`
- `src/safety/projection.py`
- `src/ood/risk.py`
- `scripts/run_risk_and_projection_checks.py`

拆分规则：

\[
hard = S^e + S^h
\]

\[
soft = D^h + C^{pv} + C^{wind}
\]

其中 hard safety cost 只统计电失负荷和热失负荷；soft operation cost 统计热倾倒、弃光和弃风。环境 `info`、离线数据集 transition 表和数据集统计表均已加入：

- `hard_safety_cost`
- `soft_operation_cost`
- `safety_cost = hard_safety_cost + soft_operation_cost`

## 2. OOD 风险评分检查

本次实现了两种轻量距离评分：

- Mahalanobis 距离；
- kNN 平均近邻距离。

参考分布使用 Expert 数据中的安全样本，评分对象包括 Expert、Mixed、Poor，以及简单构造的 `load_up` 和 `efficiency_drop` 漂移样本。评价指标为 Spearman 相关、AUROC 和 AUPRC，标签为 `hard_safety_cost > 0`。

关键结果：

| 方法 | 场景 | Spearman | AUROC | AUPRC |
|---|---|---:|---:|---:|
| Mahalanobis | load_up | 0.312 | 0.567 | 0.738 |
| Mahalanobis | mixed | 0.200 | 0.534 | 0.553 |
| Mahalanobis | poor | -0.139 | 0.341 | 0.290 |
| kNN | expert | 0.308 | 0.646 | 0.646 |
| kNN | load_up | 0.163 | 0.513 | 0.669 |

结论：简单距离型 OOD 分数目前不能稳定预测 hard safety risk。它对 load-up 场景有一定 AUPRC 信号，但 AUROC 和跨数据质量一致性不足。因此，下一步不能直接把 Mahalanobis/kNN 作为论文核心 OOD 模块；第 9 周应优先尝试 dynamics ensemble 或 critic ensemble uncertainty。

## 3. 物理安全投影检查

当前投影为一步启发式物理投影：在归一化动作空间内构造少量候选动作，优先增加 CHP、热泵供热，减少充电负担并释放储能，从中选择 hard safety cost 最低且距离原动作较近的动作。

压力测试使用明显不安全动作：

\[
a=[-1,-1,1,1]
\]

即 CHP 最低、热泵最低、电池充电、储热充热。

结果：

| 场景 | 投影前 hard safety | 投影后 hard safety | 平均投影距离 |
|---|---:|---:|---:|
| in_distribution | 330.74 | 0.00 | 2.40 |
| load_up | 368.00 | 0.03 | 2.61 |
| efficiency_drop | 330.74 | 0.00 | 2.40 |

结论：物理安全投影对 hard safety 的削减非常明显，值得进入第 10 周正式模块。但当前版本是启发式候选投影，不是严格 QP/LP 最小距离投影；论文正式版本应将其升级为可解释的约束投影优化问题，并报告投影距离和计算时间。

## 4. 更新后的止损判断

综合结果：

- hard/soft 成本拆分：通过，必须保留。
- OOD 距离分数：弱通过/预警，不能作为最终主方法。
- 物理投影：通过，值得继续。

因此路线应调整为：

> 继续推进物理安全投影；OOD 模块从简单距离评分转为 ensemble uncertainty。如果第 9 周 ensemble OOD 仍不能预测 hard safety risk，则论文主张应删除“OOD 感知”部分，转为“物理安全投影增强离线 RL 调度可靠性”。

