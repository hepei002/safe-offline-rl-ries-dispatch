# 离线强化学习数据集卡片

## 1. 数据集概览

数据集名称：`ries_offline_dispatch_prototype`

数据格式：自定义 Parquet transition 表。

数据来源：2018 年连续公开外生时序窗口，来自已处理的德国电负荷、热需求、风光出力、天气和热泵 COP 联合数据表。系统参数来自 `configs/system.yaml`，行为策略参数来自 `configs/behavior_policies.yaml`，数据集生成配置来自 `configs/offline_dataset.yaml`。

数据用途：用于第 8 周及之后的离线强化学习基线训练，包括 BC、TD3+BC、IQL、CQL 以及后续安全离线 RL 方法。

## 2. 数据质量分层

| 质量 | 行为策略组成 | 用途 |
|---|---|---|
| Expert | 完美信息 LP | 高质量专家轨迹，用作行为克隆和专家上界参照 |
| Mixed | 滚动 MPC、带噪 MPC、规则控制、安全随机混合 | 主训练集，包含优质和次优策略 |
| Poor | 规则控制和安全随机混合 | 低质量/高覆盖度数据，用于测试离线 RL 对数据质量的敏感性 |

每个 episode 长度为 24 h。当前原型配置为 Expert 180 个 episode、Mixed 60 个 episode、Poor 180 个 episode，总计 10080 个 transition，满足原型级 10,000–50,000 个 transition 的规模要求。Mixed 数据量较小，是为了在第 7 周快速迭代阶段控制滚动 MPC 求解时间；正式实验可把三类质量均扩展到全年或三年样本。

## 3. Transition schema

每行表示一个小时级 transition：

- `quality`：数据质量层级。
- `policy`：生成该 transition 的行为策略。
- `episode_id`：episode 标识。
- `step`：episode 内小时序号。
- `utc_timestamp`：UTC 时间戳。
- `obs_*`：当前状态，归一化规则见第六周环境文档。
- `action_*`：归一化动作，范围为 \([-1,1]\)。
- `reward`：单小时运行成本的相反数。
- `cost`：单小时运行成本。
- `safety_cost`：电失负荷、热失负荷、热倾倒、弃风弃光之和。
- `next_obs_*`：下一状态。
- `terminal`：是否为 episode 最后一步。
- `truncated`：是否异常截断，当前原型均为 `False`。

附加调度字段包括购售电、CHP、热泵、SOC、失负荷、弃能和电热平衡残差，用于审计和安全约束分析。

## 4. 文件位置

数据集文件：

- `data/processed/offline/expert.parquet`
- `data/processed/offline/mixed.parquet`
- `data/processed/offline/poor.parquet`

统计与元数据：

- `data/processed/offline/dataset_quality_summary.csv`
- `data/processed/offline/metadata.yaml`

覆盖度图：

- `results/figures/offline_dataset/offline_dataset_coverage.png`
- `results/figures/offline_dataset/offline_dataset_coverage.pdf`
- `results/figures/offline_dataset/offline_dataset_coverage.svg`
- `results/figures/offline_dataset/offline_dataset_coverage.tiff`

## 5. 质量控制

数据生成时执行以下检查：

1. 所有 transition 均来自同一个 Gymnasium 环境动力学。
2. 动作被编码到统一 \([-1,1]\) 空间。
3. 状态和下一状态使用同一归一化规则。
4. 电热平衡残差保存在数据表中，可用于训练前审计。
5. `safety_cost` 显式记录安全风险，不把失负荷和弃能隐藏在 reward 中。

## 6. 使用限制

当前数据集是原型级数据集，不应用于最终论文主实验的全部结论。正式实验前建议：

- 将 episode 数量扩展到 365 天或三年全样本。
- 单独保留跨年份测试集，例如 2019 年作为 out-of-distribution 或 hold-out evaluation。
- 固定随机种子并保存所有策略版本号。
- 根据第 8 周离线 RL 训练结果，调整 Expert/Mixed/Poor 的比例。

## 7. 本次原型数据集统计

本次生成结果显示三类数据质量具有清晰差异：Expert 的平均 episode return 最高，Mixed 居中，Poor 最低；Poor 的 soft operation cost 最高，Mixed/Poor 的 hard safety cost 高于 Expert，说明数据集中同时包含安全和非安全、优质和次优轨迹。

| 质量 | transitions | episodes | 策略组成 | 平均 episode return | hard safety | soft operation | 动作覆盖度 |
|---|---:|---:|---|---:|---:|---:|---:|
| Expert | 4320 | 180 | perfect_information_lp:4320 | -38614.46 | 2.66 | 4.41 | 0.572 |
| Mixed | 1440 | 60 | noisy_mpc:360; rolling_mpc:360; rule:360; random:360 | -151963.66 | 16.31 | 12.62 | 0.520 |
| Poor | 4320 | 180 | rule:1728; random:2592 | -165619.87 | 18.20 | 66.73 | 0.487 |

当前已经将 `safety_cost` 拆为两类：`hard_safety_cost` 表示电/热失负荷，`soft_operation_cost` 表示热倾倒和弃风弃光。后续安全约束和 OOD 风险验证应优先使用 `hard_safety_cost`，避免把弃能或热倾倒误判为供能不可行。
