# 第13周：完整基线实验

本周运行统一预算下的主基线实验。训练预算为 80 gradient steps，RL 方法使用 5 个随机种子，评估场景为 in-distribution、load-up、cold-wave extreme 和 compound extreme。

## 主结果表

| method | scenario | seeds | mean_episode_cost_eur | mean_hard_safety_cost | mean_projection_distance_l2 | intervention_rate | mean_decision_time_ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cql | cold_wave_extreme | 5 | 414519.368 | 49.934 | 0.000 | 0.000 | 0.255 |
| cql | compound_extreme | 5 | 538233.175 | 64.492 | 0.000 | 0.000 | 0.259 |
| cql | in_distribution | 5 | 23991.494 | 1.274 | 0.000 | 0.000 | 0.263 |
| cql | load_up_20 | 5 | 117282.367 | 12.547 | 0.000 | 0.000 | 0.256 |
| cql_adaptive_safety | cold_wave_extreme | 5 | 16379.917 | 0.000 | 0.477 | 0.733 | 173.296 |
| cql_adaptive_safety | compound_extreme | 5 | 25088.593 | 0.000 | 0.574 | 0.783 | 146.487 |
| cql_adaptive_safety | in_distribution | 5 | 13852.898 | 0.000 | 0.014 | 0.117 | 390.111 |
| cql_adaptive_safety | load_up_20 | 5 | 17373.808 | 0.000 | 0.154 | 0.600 | 228.543 |
| iql | cold_wave_extreme | 5 | 480323.127 | 58.205 | 0.000 | 0.000 | 0.259 |
| iql | compound_extreme | 5 | 620851.452 | 74.891 | 0.000 | 0.000 | 0.266 |
| iql | in_distribution | 5 | 45033.557 | 3.927 | 0.000 | 0.000 | 0.282 |
| iql | load_up_20 | 5 | 177661.848 | 20.123 | 0.000 | 0.000 | 0.259 |
| iql_adaptive_safety | cold_wave_extreme | 5 | 16702.878 | 0.000 | 0.506 | 0.775 | 159.931 |
| iql_adaptive_safety | compound_extreme | 5 | 24535.666 | 0.000 | 0.661 | 0.833 | 142.914 |
| iql_adaptive_safety | in_distribution | 5 | 13757.942 | 0.000 | 0.036 | 0.200 | 392.539 |
| iql_adaptive_safety | load_up_20 | 5 | 17342.865 | 0.000 | 0.229 | 0.700 | 192.735 |
| iql_fixed_safety | cold_wave_extreme | 5 | 17331.575 | 0.000 | 0.629 | 0.775 | 146.067 |
| iql_fixed_safety | compound_extreme | 5 | 24885.113 | 0.000 | 0.737 | 0.833 | 116.172 |
| iql_fixed_safety | in_distribution | 5 | 13875.284 | 0.000 | 0.064 | 0.200 | 384.961 |
| iql_fixed_safety | load_up_20 | 5 | 18142.877 | 0.000 | 0.440 | 0.700 | 172.597 |
| perfect_information_lp | cold_wave_extreme | 1 | 15025.627 | 0.000 | 0.000 | 0.000 | 0.316 |
| perfect_information_lp | compound_extreme | 1 | 21975.402 | 0.000 | 0.000 | 0.000 | 0.352 |
| perfect_information_lp | in_distribution | 1 | 11187.561 | 0.000 | 0.000 | 0.000 | 0.463 |
| perfect_information_lp | load_up_20 | 1 | 14841.636 | 0.000 | 0.000 | 0.000 | 0.352 |
| rolling_mpc | cold_wave_extreme | 1 | 15402.483 | 0.000 | 0.000 | 0.000 | 7.710 |
| rolling_mpc | compound_extreme | 1 | 22362.496 | 0.000 | 0.000 | 0.000 | 7.547 |
| rolling_mpc | in_distribution | 1 | 11187.449 | 0.000 | 0.000 | 0.000 | 8.990 |
| rolling_mpc | load_up_20 | 1 | 14944.932 | 0.000 | 0.000 | 0.000 | 7.986 |
| rule_based | cold_wave_extreme | 1 | 17196.555 | 0.000 | 0.000 | 0.000 | 0.221 |
| rule_based | compound_extreme | 1 | 23220.995 | 0.000 | 0.000 | 0.000 | 0.189 |
| rule_based | in_distribution | 1 | 13058.578 | 0.000 | 0.000 | 0.000 | 0.202 |
| rule_based | load_up_20 | 1 | 16655.317 | 0.000 | 0.000 | 0.000 | 0.188 |

## 计算效率表

| method | mean_decision_time_ms | mean_projection_distance_l2 | intervention_rate |
| --- | --- | --- | --- |
| bc | 0.297 | 0.000 | 0.000 |
| cql | 0.258 | 0.000 | 0.000 |
| cql_adaptive_safety | 234.609 | 0.305 | 0.558 |
| cql_fixed_safety | 225.382 | 0.401 | 0.556 |
| cql_ood_warning | 0.259 | 0.000 | 0.000 |
| iql | 0.267 | 0.000 | 0.000 |
| iql_adaptive_safety | 222.030 | 0.358 | 0.627 |
| iql_fixed_safety | 204.949 | 0.468 | 0.627 |
| iql_ood_warning | 0.266 | 0.000 | 0.000 |
| perfect_information_lp | 0.371 | 0.000 | 0.000 |
| rolling_mpc | 8.058 | 0.000 | 0.000 |
| rule_based | 0.200 | 0.000 | 0.000 |
| td3_bc | 0.254 | 0.000 | 0.000 |

## 原始实验清单

| algorithm | seed | dataset | train_time_s | steps |
| --- | --- | --- | --- | --- |
| bc | 0 | all | 0.680 | 80 |
| bc | 1 | all | 0.134 | 80 |
| bc | 2 | all | 0.131 | 80 |
| bc | 3 | all | 0.152 | 80 |
| bc | 4 | all | 0.126 | 80 |
| td3_bc | 0 | all | 0.375 | 80 |
| td3_bc | 1 | all | 0.357 | 80 |
| td3_bc | 2 | all | 0.371 | 80 |
| td3_bc | 3 | all | 0.375 | 80 |
| td3_bc | 4 | all | 0.393 | 80 |
| cql | 0 | all | 0.491 | 80 |
| cql | 1 | all | 0.529 | 80 |
| cql | 2 | all | 0.542 | 80 |
| cql | 3 | all | 0.493 | 80 |
| cql | 4 | all | 0.523 | 80 |
| iql | 0 | all | 0.559 | 80 |
| iql | 1 | all | 0.491 | 80 |
| iql | 2 | all | 0.656 | 80 |
| iql | 3 | all | 0.563 | 80 |
| iql | 4 | all | 0.494 | 80 |

结果文件：

- `E:\研究内容\论文\AE\results\week13_14_experiments\week13_raw_results.csv`
- `E:\研究内容\论文\AE\results\week13_14_experiments\week13_main_summary.csv`
- `E:\研究内容\论文\AE\results\week13_14_experiments\week13_efficiency_table.csv`
- `E:\研究内容\论文\AE\results\week13_14_experiments\week13_experiment_manifest.csv`
- `E:\研究内容\论文\AE\results\figures\week13_14\week13_main_results.png`
