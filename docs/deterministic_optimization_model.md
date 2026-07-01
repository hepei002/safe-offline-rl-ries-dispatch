# 第四周：确定性优化调度模型

本文档给出区域综合能源系统的 24 h 确定性日前调度模型。该模型用于三类目的：一是形成可解释的优化基线，二是为后续离线强化学习生成专家调度标签，三是为分布漂移场景下的安全性评价提供物理约束参照。

## 1. 建模对象与典型日

系统对象为中型工业园区综合能源系统，时间分辨率为 1 h，调度窗口为 24 h。外生输入包括电负荷、热负荷、光伏可用功率、风电可用功率、空气源热泵 COP 和气温。设备包括电网交互、光伏、风电、燃气 CHP、空气源热泵、电池和热储能。

典型日采用“日特征向量最接近季节中位数”的方法选择：

| 典型日 | 月份集合 | 选择特征 |
|---|---:|---|
| 冬季典型日 | 12, 1, 2 | 电负荷、热负荷、气温 |
| 夏季典型日 | 6, 7, 8 | 电负荷、热负荷、气温 |
| 过渡季典型日 | 3, 4, 5, 9, 10, 11 | 电负荷、热负荷、气温 |

## 2. 集合、变量与参数

集合 \(t\in\mathcal{T}=\{1,\ldots,24\}\) 表示小时。主要决策变量如下。

| 符号 | 含义 | 单位 |
|---|---|---:|
| \(P^{\mathrm{imp}}_t, P^{\mathrm{exp}}_t\) | 电网购电、上网功率 | MW |
| \(P^{\mathrm{chp}}_t\) | CHP 发电功率 | MW |
| \(H^{\mathrm{hp}}_t\) | 热泵供热功率 | MWth |
| \(P^{\mathrm{bc}}_t, P^{\mathrm{bd}}_t\) | 电池充电、放电功率 | MW |
| \(E^{\mathrm{b}}_t\) | 电池能量状态 | MWh |
| \(H^{\mathrm{tc}}_t, H^{\mathrm{td}}_t\) | 储热充热、放热功率 | MWth |
| \(E^{\mathrm{h}}_t\) | 储热能量状态 | MWhth |
| \(S^{\mathrm{e}}_t, S^{\mathrm{h}}_t\) | 电、热失负荷 | MW / MWth |
| \(C^{\mathrm{pv}}_t, C^{\mathrm{w}}_t\) | 光伏、风电弃电 | MW |

外生参数包括电负荷 \(L^{\mathrm{e}}_t\)、热负荷 \(L^{\mathrm{h}}_t\)、光伏可用功率 \(\bar P^{\mathrm{pv}}_t\)、风电可用功率 \(\bar P^{\mathrm{w}}_t\)、热泵 COP \(COP_t\) 和分时购电价格 \(\pi^{\mathrm{imp}}_t\)。设备容量、效率和爬坡参数来自 `configs/system.yaml`；成本假设来自 `configs/deterministic_dispatch.yaml`。

## 3. 目标函数

确定性调度以运行成本最小为目标：

\[
\min \sum_{t\in\mathcal{T}} \left(
\pi^{\mathrm{imp}}_t P^{\mathrm{imp}}_t
- \pi^{\mathrm{exp}} P^{\mathrm{exp}}_t
+ \pi^{\mathrm{gas}}\frac{P^{\mathrm{chp}}_t}{\eta^{\mathrm{chp,e}}}
+ \pi^{\mathrm{curt}}(C^{\mathrm{pv}}_t+C^{\mathrm{w}}_t)
+ \pi^{\mathrm{shed,e}}S^{\mathrm{e}}_t
+ \pi^{\mathrm{shed,h}}S^{\mathrm{h}}_t
\right).
\]

失负荷惩罚设置为远高于正常运行成本，因此只在物理容量不足时启用；弃风弃光设置小惩罚，用于优先消纳可再生能源。

## 4. 功率平衡约束

电功率平衡为：

\[
P^{\mathrm{imp}}_t-P^{\mathrm{exp}}_t+P^{\mathrm{chp}}_t
+(\bar P^{\mathrm{pv}}_t-C^{\mathrm{pv}}_t)
+(\bar P^{\mathrm{w}}_t-C^{\mathrm{w}}_t)
+P^{\mathrm{bd}}_t-P^{\mathrm{bc}}_t
-\frac{H^{\mathrm{hp}}_t}{COP_t}
+S^{\mathrm{e}}_t
=L^{\mathrm{e}}_t.
\]

热功率平衡为：

\[
\rho^{\mathrm{chp}}P^{\mathrm{chp}}_t+H^{\mathrm{hp}}_t
+H^{\mathrm{td}}_t-H^{\mathrm{tc}}_t
+S^{\mathrm{h}}_t
=L^{\mathrm{h}}_t.
\]

其中 \(\rho^{\mathrm{chp}}\) 为 CHP 热电比。

## 5. 设备运行约束

电网交互：

\[
0\le P^{\mathrm{imp}}_t\le \bar P^{\mathrm{imp}},\quad
0\le P^{\mathrm{exp}}_t\le \bar P^{\mathrm{exp}}.
\]

CHP 与热泵容量及爬坡：

\[
0\le P^{\mathrm{chp}}_t\le \bar P^{\mathrm{chp}},\quad
0\le H^{\mathrm{hp}}_t\le \bar H^{\mathrm{hp}},
\]

\[
-R^{\mathrm{chp,down}}\le P^{\mathrm{chp}}_t-P^{\mathrm{chp}}_{t-1}\le R^{\mathrm{chp,up}},
\]

\[
-R^{\mathrm{hp,down}}\le H^{\mathrm{hp}}_t-H^{\mathrm{hp}}_{t-1}\le R^{\mathrm{hp,up}}.
\]

电池动态：

\[
E^{\mathrm{b}}_t=(1-\lambda^{\mathrm{b}})E^{\mathrm{b}}_{t-1}
+\eta^{\mathrm{bc}}P^{\mathrm{bc}}_t
-\frac{P^{\mathrm{bd}}_t}{\eta^{\mathrm{bd}}},
\]

\[
\underline{s}^{\mathrm{b}}\bar E^{\mathrm{b}}\le E^{\mathrm{b}}_t\le
\overline{s}^{\mathrm{b}}\bar E^{\mathrm{b}},\quad
0\le P^{\mathrm{bc}}_t\le \bar P^{\mathrm{bc}},\quad
0\le P^{\mathrm{bd}}_t\le \bar P^{\mathrm{bd}}.
\]

储热动态：

\[
E^{\mathrm{h}}_t=(1-\lambda^{\mathrm{h}})E^{\mathrm{h}}_{t-1}
+\eta^{\mathrm{hc}}H^{\mathrm{tc}}_t
-\frac{H^{\mathrm{td}}_t}{\eta^{\mathrm{hd}}},
\]

\[
\underline{s}^{\mathrm{h}}\bar E^{\mathrm{h}}\le E^{\mathrm{h}}_t\le
\overline{s}^{\mathrm{h}}\bar E^{\mathrm{h}},\quad
0\le H^{\mathrm{tc}}_t\le \bar H^{\mathrm{tc}},\quad
0\le H^{\mathrm{td}}_t\le \bar H^{\mathrm{td}}.
\]

为避免 24 h 窗口人为透支储能，采用循环终端约束：

\[
E^{\mathrm{b}}_{24}=E^{\mathrm{b}}_0,\quad E^{\mathrm{h}}_{24}=E^{\mathrm{h}}_0.
\]

可再生能源弃电边界：

\[
0\le C^{\mathrm{pv}}_t\le \bar P^{\mathrm{pv}}_t,\quad
0\le C^{\mathrm{w}}_t\le \bar P^{\mathrm{w}}_t.
\]

## 6. 输出与后续用途

模型输出每小时设备功率、储能 SOC、购售电、弃电、失负荷和目标函数值。它可作为论文实验中的三类基线：

1. 与规则调度比较，检验优化模型的经济性和可再生消纳能力。
2. 与在线/离线强化学习策略比较，作为确定性专家上界或近似专家。
3. 在轻度、中度、严重分布漂移场景中复用同一物理约束，评估策略安全性和可行性。

需要注意的是，该模型使用完美预测，因此不代表真实日前预测误差下的实际最优运行；后续可在鲁棒优化、随机优化和安全离线强化学习中逐步放松该假设。

## 7. 本次三典型日求解结果

本次运行脚本 `scripts/run_deterministic_dispatch.py` 后得到以下确定性调度结果。三类典型日均未出现电失负荷和热失负荷，说明在基准设备容量下，确定性优化模型可以满足典型日电热需求。

| 典型日 | 日期 UTC | 目标函数值 € | 电失负荷 MWh | 热失负荷 MWhth | 弃风弃光 MWh | 购电 MWh | CHP 发电 MWh | 热泵供热 MWhth |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 冬季 | 2018-01-19 | 22271.21 | 0.00 | 0.00 | 0.00 | 108.42 | 90.88 | 95.32 |
| 夏季 | 2018-08-14 | 14118.65 | 0.00 | 0.00 | 0.00 | 110.52 | 21.26 | 1.81 |
| 过渡季 | 2019-05-02 | 14256.86 | 0.00 | 0.00 | 0.00 | 72.74 | 56.08 | 26.77 |

对应图件位于 `results/figures/deterministic_dispatch/`，源数据位于 `results/figures/deterministic_dispatch/source_data/`。该结果可以直接作为后续“规则调度—确定性优化—离线强化学习—安全离线强化学习”的基线链条中的第二层。
