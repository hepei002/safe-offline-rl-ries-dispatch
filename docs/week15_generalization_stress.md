# 第15周：泛化与压力测试

本周进行跨年份、跨季节、气候区代理和联合压力测试。压力场景包括寒潮、热浪/低光照、连续低风光、价格尖峰和设备性能退化。结果不隐藏失败边界：未加安全层的 RL 在多数压力场景仍出现明显 hard safety violation，而 adaptive safety 能显著降低风险，但在极端复合压力下仍可能存在残余或较高干预成本。

## 压力测试表

| method | scenario | family | mean_episode_cost_eur | mean_episode_hard_safety_cost | unsafe_episode_rate | intervention_rate | mean_decision_time_ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| perfect_information_lp | year_2017_winter | cross_year | 27152.174 | 0.000 | 0.000 | 0.000 | 0.370 |
| rolling_mpc | year_2017_winter | cross_year | 27452.691 | 0.000 | 0.000 | 0.000 | 7.706 |
| rule_based | year_2017_winter | cross_year | 28324.065 | 0.000 | 0.000 | 0.000 | 0.209 |
| cql_adaptive_safety | year_2017_winter | cross_year | 30349.127 | 0.000 | 0.000 | 0.792 | 145.931 |
| iql | year_2017_winter | cross_year | 508054.354 | 60.102 | 1.000 | 0.000 | 0.282 |
| iql_adaptive_safety | year_2017_winter | cross_year | 30089.844 | 0.000 | 0.000 | 0.833 | 197.194 |
| perfect_information_lp | year_2018_winter | cross_year | 18598.824 | 0.000 | 0.000 | 0.000 | 0.310 |
| rolling_mpc | year_2018_winter | cross_year | 18584.657 | 0.000 | 0.000 | 0.000 | 7.255 |
| rule_based | year_2018_winter | cross_year | 19892.823 | 0.000 | 0.000 | 0.000 | 0.233 |
| cql_adaptive_safety | year_2018_winter | cross_year | 21288.022 | 0.000 | 0.000 | 0.708 | 165.639 |
| iql | year_2018_winter | cross_year | 276428.882 | 32.111 | 1.000 | 0.000 | 0.248 |
| iql_adaptive_safety | year_2018_winter | cross_year | 20791.298 | 0.000 | 0.000 | 0.708 | 202.932 |
| perfect_information_lp | year_2019_winter | cross_year | 17871.952 | 0.000 | 0.000 | 0.000 | 0.339 |
| rolling_mpc | year_2019_winter | cross_year | 17869.378 | 0.000 | 0.000 | 0.000 | 8.654 |
| rule_based | year_2019_winter | cross_year | 19574.105 | 0.000 | 0.000 | 0.000 | 0.163 |
| cql_adaptive_safety | year_2019_winter | cross_year | 21220.868 | 0.000 | 0.000 | 0.458 | 282.278 |
| iql | year_2019_winter | cross_year | 100180.478 | 9.979 | 1.000 | 0.000 | 0.282 |
| iql_adaptive_safety | year_2019_winter | cross_year | 20854.747 | 0.000 | 0.000 | 0.583 | 224.105 |
| perfect_information_lp | summer_peak | cross_season | 16721.796 | 0.000 | 0.000 | 0.000 | 0.389 |
| rolling_mpc | summer_peak | cross_season | 16721.796 | 0.000 | 0.000 | 0.000 | 8.164 |
| rule_based | summer_peak | cross_season | 17104.619 | 0.000 | 0.000 | 0.000 | 0.211 |
| cql_adaptive_safety | summer_peak | cross_season | 22014.367 | 0.000 | 0.000 | 0.000 | 4.424 |
| iql | summer_peak | cross_season | 22128.811 | 0.000 | 0.000 | 0.000 | 0.267 |
| iql_adaptive_safety | summer_peak | cross_season | 22128.811 | 0.000 | 0.000 | 0.000 | 3.842 |
| perfect_information_lp | shoulder_season | cross_season | 16081.296 | 0.000 | 0.000 | 0.000 | 0.309 |
| rolling_mpc | shoulder_season | cross_season | 16081.296 | 0.000 | 0.000 | 0.000 | 7.615 |
| rule_based | shoulder_season | cross_season | 16611.684 | 0.000 | 0.000 | 0.000 | 0.177 |
| cql_adaptive_safety | shoulder_season | cross_season | 21292.709 | 0.000 | 0.000 | 0.000 | 3.717 |
| iql | shoulder_season | cross_season | 21382.132 | 0.000 | 0.000 | 0.000 | 0.240 |
| iql_adaptive_safety | shoulder_season | cross_season | 21382.132 | 0.000 | 0.000 | 0.000 | 3.873 |
| perfect_information_lp | cold_climate_zone | climate_zone | 21264.346 | 0.000 | 0.000 | 0.000 | 0.320 |
| rolling_mpc | cold_climate_zone | climate_zone | 21374.483 | 0.000 | 0.000 | 0.000 | 7.674 |
| rule_based | cold_climate_zone | climate_zone | 22530.315 | 0.000 | 0.000 | 0.000 | 0.192 |
| cql_adaptive_safety | cold_climate_zone | climate_zone | 24462.210 | 0.000 | 0.000 | 0.750 | 168.291 |
| iql | cold_climate_zone | climate_zone | 531182.470 | 63.740 | 1.000 | 0.000 | 0.259 |
| iql_adaptive_safety | cold_climate_zone | climate_zone | 24312.025 | 0.000 | 0.000 | 0.792 | 155.859 |
| perfect_information_lp | warm_low_solar_zone | climate_zone | 18423.541 | 0.000 | 0.000 | 0.000 | 0.329 |
| rolling_mpc | warm_low_solar_zone | climate_zone | 18423.539 | 0.000 | 0.000 | 0.000 | 7.360 |
| rule_based | warm_low_solar_zone | climate_zone | 18872.999 | 0.000 | 0.000 | 0.000 | 0.195 |
| cql_adaptive_safety | warm_low_solar_zone | climate_zone | 23620.396 | 0.000 | 0.000 | 0.000 | 441.525 |
| iql | warm_low_solar_zone | climate_zone | 23704.604 | 0.000 | 0.000 | 0.000 | 0.270 |
| iql_adaptive_safety | warm_low_solar_zone | climate_zone | 23704.604 | 0.000 | 0.000 | 0.000 | 485.807 |
| perfect_information_lp | price_spike_low_renewable | compound_stress | 25591.929 | 0.000 | 0.000 | 0.000 | 0.318 |
| rolling_mpc | price_spike_low_renewable | compound_stress | 25623.870 | 0.000 | 0.000 | 0.000 | 7.338 |
| rule_based | price_spike_low_renewable | compound_stress | 33469.666 | 0.000 | 0.000 | 0.000 | 0.181 |
| cql_adaptive_safety | price_spike_low_renewable | compound_stress | 42448.064 | 0.000 | 0.000 | 0.458 | 311.150 |
| iql | price_spike_low_renewable | compound_stress | 131464.685 | 11.328 | 1.000 | 0.000 | 0.255 |
| iql_adaptive_safety | price_spike_low_renewable | compound_stress | 42418.844 | 0.000 | 0.000 | 0.708 | 192.841 |
| perfect_information_lp | cold_wave_device_fault | compound_stress | 30618.527 | 0.000 | 0.000 | 0.000 | 0.344 |
| rolling_mpc | cold_wave_device_fault | compound_stress | 30618.527 | 0.000 | 0.000 | 0.000 | 7.439 |
| rule_based | cold_wave_device_fault | compound_stress | 31693.824 | 0.000 | 0.000 | 0.000 | 0.186 |
| cql_adaptive_safety | cold_wave_device_fault | compound_stress | 32847.613 | 0.000 | 0.000 | 0.875 | 102.202 |
| iql | cold_wave_device_fault | compound_stress | 964072.074 | 117.076 | 1.000 | 0.000 | 0.280 |
| iql_adaptive_safety | cold_wave_device_fault | compound_stress | 32515.716 | 0.000 | 0.000 | 0.958 | 63.220 |
| perfect_information_lp | three_day_low_renewable | compound_stress | 26306.657 | 0.000 | 0.000 | 0.000 | 0.313 |
| rolling_mpc | three_day_low_renewable | compound_stress | 26573.716 | 0.000 | 0.000 | 0.000 | 7.422 |
| rule_based | three_day_low_renewable | compound_stress | 27483.894 | 0.000 | 0.000 | 0.000 | 0.198 |
| cql_adaptive_safety | three_day_low_renewable | compound_stress | 30123.663 | 0.000 | 0.000 | 0.792 | 128.937 |
| iql | three_day_low_renewable | compound_stress | 501135.623 | 59.340 | 1.000 | 0.000 | 0.291 |
| iql_adaptive_safety | three_day_low_renewable | compound_stress | 29893.982 | 0.000 | 0.000 | 0.792 | 162.475 |

## 失败模式清单

| method | scenario | mean_episode_hard_safety_cost | unsafe_episode_rate | mean_episode_cost_eur | failure_mode |
| --- | --- | --- | --- | --- | --- |
| iql | cold_wave_device_fault | 117.076 | 1.000 | 964072.074 | residual_hard_safety_violation |
| cql | cold_wave_device_fault | 106.440 | 1.000 | 879696.629 | residual_hard_safety_violation |
| iql | compound_extreme | 96.659 | 1.000 | 794232.809 | residual_hard_safety_violation |
| iql_ood_warning | compound_extreme | 96.659 | 1.000 | 794232.809 | residual_hard_safety_violation |
| bc | compound_extreme | 94.891 | 1.000 | 780210.607 | residual_hard_safety_violation |
| bc | compound_extreme | 88.735 | 1.000 | 730836.203 | residual_hard_safety_violation |
| bc | compound_extreme | 82.719 | 1.000 | 683037.189 | residual_hard_safety_violation |
| iql | cold_wave_extreme | 79.167 | 1.000 | 647069.910 | residual_hard_safety_violation |
| iql_ood_warning | cold_wave_extreme | 79.167 | 1.000 | 647069.910 | residual_hard_safety_violation |
| bc | compound_extreme | 78.973 | 1.000 | 653127.895 | residual_hard_safety_violation |
| bc | cold_wave_extreme | 76.893 | 1.000 | 629055.437 | residual_hard_safety_violation |
| td3_bc | compound_extreme | 75.726 | 1.000 | 628012.553 | residual_hard_safety_violation |
| iql | compound_extreme | 75.138 | 1.000 | 622909.925 | residual_hard_safety_violation |
| iql_ood_warning | compound_extreme | 75.138 | 1.000 | 622909.925 | residual_hard_safety_violation |
| bc | compound_extreme | 74.256 | 1.000 | 615840.786 | residual_hard_safety_violation |
| cql | compound_extreme | 73.296 | 1.000 | 608418.665 | residual_hard_safety_violation |
| cql_ood_warning | compound_extreme | 73.296 | 1.000 | 608418.665 | residual_hard_safety_violation |
| iql | compound_extreme | 70.833 | 1.000 | 588247.226 | residual_hard_safety_violation |
| iql_ood_warning | compound_extreme | 70.833 | 1.000 | 588247.226 | residual_hard_safety_violation |
| bc | cold_wave_extreme | 70.302 | 1.000 | 576239.765 | residual_hard_safety_violation |
| cql | compound_extreme | 68.622 | 1.000 | 571414.816 | residual_hard_safety_violation |
| cql_ood_warning | compound_extreme | 68.622 | 1.000 | 571414.816 | residual_hard_safety_violation |
| iql | compound_extreme | 66.896 | 1.000 | 557572.342 | residual_hard_safety_violation |
| iql_ood_warning | compound_extreme | 66.896 | 1.000 | 557572.342 | residual_hard_safety_violation |
| iql | compound_extreme | 64.927 | 1.000 | 541294.960 | residual_hard_safety_violation |
| iql_ood_warning | compound_extreme | 64.927 | 1.000 | 541294.960 | residual_hard_safety_violation |
| td3_bc | compound_extreme | 64.079 | 1.000 | 535426.306 | residual_hard_safety_violation |
| iql | cold_climate_zone | 63.740 | 1.000 | 531182.470 | residual_hard_safety_violation |
| cql | compound_extreme | 63.648 | 1.000 | 531372.519 | residual_hard_safety_violation |
| cql_ood_warning | compound_extreme | 63.648 | 1.000 | 531372.519 | residual_hard_safety_violation |

图件：

- `E:\研究内容\论文\AE\results\figures\week15_16\week15_stress_summary.png`
- `E:\研究内容\论文\AE\results\figures\week15_16\week15_intervention_trajectory.png`
