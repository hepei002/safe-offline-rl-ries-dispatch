# 第14周：消融、数据质量和敏感性实验

本周围绕完整方法进行初步消融和敏感性分析：去掉 OOD 检测、去掉物理投影、固定投影替代自适应投影、OOD 只报警不控制、Expert/Mixed/Poor 数据质量比较，以及 OOD 阈值、投影权重、数据规模和压力强度敏感性。

## 消融表

| method | scenario | mean_hard_safety_cost | mean_projection_distance_l2 | intervention_rate | mean_decision_time_ms |
| --- | --- | --- | --- | --- | --- |
| cql | cold_wave_extreme | 49.934 | 0.000 | 0.000 | 0.255 |
| cql | compound_extreme | 64.492 | 0.000 | 0.000 | 0.259 |
| cql | in_distribution | 1.274 | 0.000 | 0.000 | 0.263 |
| cql | load_up_20 | 12.547 | 0.000 | 0.000 | 0.256 |
| cql_adaptive_safety | cold_wave_extreme | 0.000 | 0.477 | 0.733 | 173.296 |
| cql_adaptive_safety | compound_extreme | 0.000 | 0.574 | 0.783 | 146.487 |
| cql_adaptive_safety | in_distribution | 0.000 | 0.014 | 0.117 | 390.111 |
| cql_adaptive_safety | load_up_20 | 0.000 | 0.154 | 0.600 | 228.543 |
| cql_fixed_safety | cold_wave_extreme | 0.000 | 0.543 | 0.733 | 151.754 |
| cql_fixed_safety | compound_extreme | 0.000 | 0.661 | 0.783 | 129.077 |
| cql_fixed_safety | in_distribution | 0.000 | 0.036 | 0.108 | 404.982 |
| cql_fixed_safety | load_up_20 | 0.000 | 0.364 | 0.600 | 215.713 |
| cql_ood_warning | cold_wave_extreme | 49.934 | 0.000 | 0.000 | 0.253 |
| cql_ood_warning | compound_extreme | 64.492 | 0.000 | 0.000 | 0.267 |
| cql_ood_warning | in_distribution | 1.274 | 0.000 | 0.000 | 0.248 |
| cql_ood_warning | load_up_20 | 12.547 | 0.000 | 0.000 | 0.269 |
| iql | cold_wave_extreme | 58.205 | 0.000 | 0.000 | 0.259 |
| iql | compound_extreme | 74.891 | 0.000 | 0.000 | 0.266 |
| iql | in_distribution | 3.927 | 0.000 | 0.000 | 0.282 |
| iql | load_up_20 | 20.123 | 0.000 | 0.000 | 0.259 |
| iql_adaptive_safety | cold_wave_extreme | 0.000 | 0.506 | 0.775 | 159.931 |
| iql_adaptive_safety | compound_extreme | 0.000 | 0.661 | 0.833 | 142.914 |
| iql_adaptive_safety | in_distribution | 0.000 | 0.036 | 0.200 | 392.539 |
| iql_adaptive_safety | load_up_20 | 0.000 | 0.229 | 0.700 | 192.735 |
| iql_fixed_safety | cold_wave_extreme | 0.000 | 0.629 | 0.775 | 146.067 |
| iql_fixed_safety | compound_extreme | 0.000 | 0.737 | 0.833 | 116.172 |
| iql_fixed_safety | in_distribution | 0.000 | 0.064 | 0.200 | 384.961 |
| iql_fixed_safety | load_up_20 | 0.000 | 0.440 | 0.700 | 172.597 |
| iql_ood_warning | cold_wave_extreme | 58.205 | 0.000 | 0.000 | 0.261 |
| iql_ood_warning | compound_extreme | 74.891 | 0.000 | 0.000 | 0.249 |
| iql_ood_warning | in_distribution | 3.927 | 0.000 | 0.000 | 0.305 |
| iql_ood_warning | load_up_20 | 20.123 | 0.000 | 0.000 | 0.250 |

## 敏感性结果

| sensitivity | level | mean_episode_cost_eur | mean_episode_hard_safety_cost | mean_projection_distance_l2 | mean_decision_time_ms |
| --- | --- | --- | --- | --- | --- |
| ood_threshold | 2.5-3.5 | 25311.020 | 0.000 | 0.700 | 134.377 |
| ood_threshold | 3.0-4.0 | 24943.326 | 0.000 | 0.630 | 152.597 |
| ood_threshold | 3.5-4.5 | 24943.326 | 0.000 | 0.630 | 151.601 |
| distance_weight | 0.5 | 25311.020 | 0.000 | 0.700 | 146.248 |
| distance_weight | 1.0 | 25311.020 | 0.000 | 0.700 | 130.947 |
| distance_weight | 2.0 | 25311.020 | 0.000 | 0.700 | 155.505 |
| load_multiplier | 1.0 | 25311.020 | 0.000 | 0.700 | 128.526 |
| load_multiplier | 1.2 | 30346.662 | 0.000 | 1.054 | 100.776 |
| load_multiplier | 1.5 | 193243.139 | 19.246 | 1.424 | 48.424 |

## 数据质量结果

| quality | seed | algorithm | mean_episode_cost_eur | mean_episode_hard_safety_cost |
| --- | --- | --- | --- | --- |
| expert | 0 | iql | 154749.705 | 17.853 |
| mixed | 0 | iql | 39627.989 | 3.183 |
| poor | 0 | iql | 14987.162 | 0.000 |

## 数据规模结果

| fraction | algorithm | mean_episode_cost_eur | mean_episode_hard_safety_cost |
| --- | --- | --- | --- |
| 0.250 | bc | 31322.681 | 2.108 |
| 0.500 | bc | 34940.460 | 2.593 |
| 1.000 | bc | 36432.467 | 2.763 |

结果文件：

- `E:\研究内容\论文\AE\results\week13_14_experiments\week14_sensitivity_results.csv`
- `E:\研究内容\论文\AE\results\week13_14_experiments\week14_data_quality_results.csv`
- `E:\研究内容\论文\AE\results\week13_14_experiments\week14_data_size_results.csv`
- `E:\研究内容\论文\AE\results\figures\week13_14\week14_ablation_sensitivity.png`
