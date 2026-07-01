# 第16周：统计分析和实验冻结

本周完成均值、标准差、95% 置信区间、成对显著性检验、CVaR、最大违反、不可行回合比例和实验注册表。最终实验版本冻结在 `configs/week13_14_experiments.yaml` 与 `configs/week15_16_experiments.yaml`。

## 95% 置信区间节选

| method | scenario | metric | n | mean | std | ci95_half_width | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc | cold_wave_extreme | mean_episode_cost_eur | 5 | 530195.353 | 71598.470 | 88901.242 | 441294.110 | 619096.595 |
| bc | cold_wave_extreme | mean_episode_hard_safety_cost | 5 | 64.501 | 8.984 | 11.155 | 53.346 | 75.656 |
| bc | compound_extreme | mean_episode_cost_eur | 5 | 692610.536 | 64573.788 | 80178.948 | 612431.588 | 772789.484 |
| bc | compound_extreme | mean_episode_hard_safety_cost | 5 | 83.915 | 8.106 | 10.066 | 73.849 | 93.980 |
| bc | in_distribution | mean_episode_cost_eur | 5 | 56251.671 | 30337.572 | 37669.071 | 18582.599 | 93920.742 |
| bc | in_distribution | mean_episode_hard_safety_cost | 5 | 5.383 | 3.812 | 4.733 | 0.650 | 10.116 |
| bc | load_up_20 | mean_episode_cost_eur | 5 | 225974.512 | 62502.889 | 77607.586 | 148366.925 | 303582.098 |
| bc | load_up_20 | mean_episode_hard_safety_cost | 5 | 26.216 | 7.837 | 9.731 | 16.485 | 35.948 |
| cql | cold_climate_zone | mean_episode_cost_eur | 1 | 476701.228 | 0.000 | 0.000 | 476701.228 | 476701.228 |
| cql | cold_climate_zone | mean_episode_hard_safety_cost | 1 | 56.855 | 0.000 | 0.000 | 56.855 | 56.855 |
| cql | cold_wave_device_fault | mean_episode_cost_eur | 1 | 879696.629 | 0.000 | 0.000 | 879696.629 | 879696.629 |
| cql | cold_wave_device_fault | mean_episode_hard_safety_cost | 1 | 106.440 | 0.000 | 0.000 | 106.440 | 106.440 |
| cql | cold_wave_extreme | mean_episode_cost_eur | 5 | 414519.368 | 56963.409 | 70729.414 | 343789.954 | 485248.783 |
| cql | cold_wave_extreme | mean_episode_hard_safety_cost | 5 | 49.934 | 7.139 | 8.865 | 41.070 | 58.799 |
| cql | compound_extreme | mean_episode_cost_eur | 5 | 538233.175 | 55630.663 | 69074.591 | 469158.584 | 607307.766 |
| cql | compound_extreme | mean_episode_hard_safety_cost | 5 | 64.492 | 6.970 | 8.654 | 55.838 | 73.147 |
| cql | in_distribution | mean_episode_cost_eur | 5 | 23991.494 | 8412.301 | 10445.251 | 13546.243 | 34436.746 |
| cql | in_distribution | mean_episode_hard_safety_cost | 5 | 1.274 | 1.063 | 1.320 | -0.046 | 2.594 |
| cql | load_up_20 | mean_episode_cost_eur | 5 | 117282.367 | 47715.104 | 59246.127 | 58036.240 | 176528.493 |
| cql | load_up_20 | mean_episode_hard_safety_cost | 5 | 12.547 | 5.983 | 7.428 | 5.119 | 19.975 |
| cql | price_spike_low_renewable | mean_episode_cost_eur | 1 | 92823.102 | 0.000 | 0.000 | 92823.102 | 92823.102 |
| cql | price_spike_low_renewable | mean_episode_hard_safety_cost | 1 | 6.440 | 0.000 | 0.000 | 6.440 | 6.440 |
| cql | shoulder_season | mean_episode_cost_eur | 1 | 21292.709 | 0.000 | 0.000 | 21292.709 | 21292.709 |
| cql | shoulder_season | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql | summer_peak | mean_episode_cost_eur | 1 | 22014.367 | 0.000 | 0.000 | 22014.367 | 22014.367 |
| cql | summer_peak | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql | three_day_low_renewable | mean_episode_cost_eur | 1 | 438024.510 | 0.000 | 0.000 | 438024.510 | 438024.510 |
| cql | three_day_low_renewable | mean_episode_hard_safety_cost | 1 | 51.374 | 0.000 | 0.000 | 51.374 | 51.374 |
| cql | warm_low_solar_zone | mean_episode_cost_eur | 1 | 23620.396 | 0.000 | 0.000 | 23620.396 | 23620.396 |
| cql | warm_low_solar_zone | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql | year_2017_winter | mean_episode_cost_eur | 1 | 443649.500 | 0.000 | 0.000 | 443649.500 | 443649.500 |
| cql | year_2017_winter | mean_episode_hard_safety_cost | 1 | 51.970 | 0.000 | 0.000 | 51.970 | 51.970 |
| cql | year_2018_winter | mean_episode_cost_eur | 1 | 232912.885 | 0.000 | 0.000 | 232912.885 | 232912.885 |
| cql | year_2018_winter | mean_episode_hard_safety_cost | 1 | 26.603 | 0.000 | 0.000 | 26.603 | 26.603 |
| cql | year_2019_winter | mean_episode_cost_eur | 1 | 65580.065 | 0.000 | 0.000 | 65580.065 | 65580.065 |
| cql | year_2019_winter | mean_episode_hard_safety_cost | 1 | 5.589 | 0.000 | 0.000 | 5.589 | 5.589 |
| cql_adaptive_safety | cold_climate_zone | mean_episode_cost_eur | 1 | 24462.210 | 0.000 | 0.000 | 24462.210 | 24462.210 |
| cql_adaptive_safety | cold_climate_zone | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | cold_wave_device_fault | mean_episode_cost_eur | 1 | 32847.613 | 0.000 | 0.000 | 32847.613 | 32847.613 |
| cql_adaptive_safety | cold_wave_device_fault | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | cold_wave_extreme | mean_episode_cost_eur | 5 | 16379.917 | 125.749 | 156.138 | 16223.779 | 16536.055 |
| cql_adaptive_safety | cold_wave_extreme | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | compound_extreme | mean_episode_cost_eur | 5 | 25088.593 | 70.287 | 87.273 | 25001.320 | 25175.866 |
| cql_adaptive_safety | compound_extreme | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 0.000 | -0.000 | 0.000 |
| cql_adaptive_safety | in_distribution | mean_episode_cost_eur | 5 | 13852.898 | 162.062 | 201.226 | 13651.672 | 14054.124 |
| cql_adaptive_safety | in_distribution | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | load_up_20 | mean_episode_cost_eur | 5 | 17373.808 | 112.135 | 139.234 | 17234.574 | 17513.041 |
| cql_adaptive_safety | load_up_20 | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 0.000 | -0.000 | 0.000 |
| cql_adaptive_safety | price_spike_low_renewable | mean_episode_cost_eur | 1 | 42448.064 | 0.000 | 0.000 | 42448.064 | 42448.064 |
| cql_adaptive_safety | price_spike_low_renewable | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | shoulder_season | mean_episode_cost_eur | 1 | 21292.709 | 0.000 | 0.000 | 21292.709 | 21292.709 |
| cql_adaptive_safety | shoulder_season | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | summer_peak | mean_episode_cost_eur | 1 | 22014.367 | 0.000 | 0.000 | 22014.367 | 22014.367 |
| cql_adaptive_safety | summer_peak | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | three_day_low_renewable | mean_episode_cost_eur | 1 | 30123.663 | 0.000 | 0.000 | 30123.663 | 30123.663 |
| cql_adaptive_safety | three_day_low_renewable | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | warm_low_solar_zone | mean_episode_cost_eur | 1 | 23620.396 | 0.000 | 0.000 | 23620.396 | 23620.396 |
| cql_adaptive_safety | warm_low_solar_zone | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cql_adaptive_safety | year_2017_winter | mean_episode_cost_eur | 1 | 30349.127 | 0.000 | 0.000 | 30349.127 | 30349.127 |
| cql_adaptive_safety | year_2017_winter | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## 成对显著性检验

| scenario | baseline | treatment | metric | n_pairs | mean_delta | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cold_climate_zone | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -63.740 | 0.000 | 1.000 |
| cold_climate_zone | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -56.855 | 0.000 | 1.000 |
| cold_climate_zone | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| cold_climate_zone | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| cold_wave_device_fault | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -117.076 | 0.000 | 1.000 |
| cold_wave_device_fault | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -106.440 | 0.000 | 1.000 |
| cold_wave_device_fault | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| cold_wave_device_fault | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| cold_wave_extreme | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -58.205 | -10.256 | 0.001 |
| cold_wave_extreme | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -49.934 | -15.640 | 0.000 |
| cold_wave_extreme | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 1.238 | 0.283 |
| cold_wave_extreme | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 0.817 | 0.460 |
| compound_extreme | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -74.891 | -13.101 | 0.000 |
| compound_extreme | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -64.492 | -20.690 | 0.000 |
| compound_extreme | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 1.494 | 0.209 |
| compound_extreme | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 0.489 | 0.650 |
| in_distribution | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -3.927 | -1.767 | 0.152 |
| in_distribution | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -1.274 | -2.680 | 0.055 |
| in_distribution | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 1.000 |
| in_distribution | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 0.000 | 1.000 |
| load_up_20 | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -20.123 | -3.949 | 0.017 |
| load_up_20 | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -12.547 | -4.690 | 0.009 |
| load_up_20 | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 5 | 0.000 | 1.817 | 0.143 |
| load_up_20 | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 5 | -0.000 | -1.579 | 0.190 |
| price_spike_low_renewable | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -11.328 | 0.000 | 1.000 |
| price_spike_low_renewable | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -6.440 | 0.000 | 1.000 |
| price_spike_low_renewable | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| price_spike_low_renewable | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| shoulder_season | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| shoulder_season | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| shoulder_season | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| shoulder_season | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| summer_peak | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| summer_peak | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| summer_peak | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| summer_peak | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| three_day_low_renewable | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -59.340 | 0.000 | 1.000 |
| three_day_low_renewable | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -51.374 | 0.000 | 1.000 |
| three_day_low_renewable | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| three_day_low_renewable | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| warm_low_solar_zone | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| warm_low_solar_zone | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | 0.000 | 0.000 | 1.000 |
| warm_low_solar_zone | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| warm_low_solar_zone | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2017_winter | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -60.102 | 0.000 | 1.000 |
| year_2017_winter | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -51.970 | 0.000 | 1.000 |
| year_2017_winter | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2017_winter | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2018_winter | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -32.111 | 0.000 | 1.000 |
| year_2018_winter | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -26.603 | 0.000 | 1.000 |
| year_2018_winter | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2018_winter | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2019_winter | iql | iql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -9.979 | 0.000 | 1.000 |
| year_2019_winter | cql | cql_adaptive_safety | mean_episode_hard_safety_cost | 1 | -5.589 | 0.000 | 1.000 |
| year_2019_winter | iql_fixed_safety | iql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |
| year_2019_winter | cql_fixed_safety | cql_adaptive_safety | mean_episode_hard_safety_cost | 0 | 0.000 | 0.000 | 1.000 |

## 尾部风险指标

| method | scenario | max_hard_safety_cost | cvar90_hard_safety_cost | cvar90_episode_cost_eur | infeasible_episode_rate |
| --- | --- | --- | --- | --- | --- |
| bc | cold_wave_extreme | 76.893 | 76.893 | 629055.437 | 1.000 |
| bc | compound_extreme | 94.891 | 94.891 | 780210.607 | 1.000 |
| bc | in_distribution | 10.565 | 10.565 | 97528.085 | 1.000 |
| bc | load_up_20 | 37.073 | 37.073 | 312641.175 | 1.000 |
| cql | cold_climate_zone | 56.855 | 56.855 | 476701.228 | 1.000 |
| cql | cold_wave_device_fault | 106.440 | 106.440 | 879696.629 | 1.000 |
| cql | cold_wave_extreme | 58.799 | 58.799 | 485180.391 | 1.000 |
| cql | compound_extreme | 73.296 | 73.296 | 608418.665 | 1.000 |
| cql | in_distribution | 2.373 | 2.373 | 32887.371 | 0.800 |
| cql | load_up_20 | 20.086 | 20.086 | 177352.991 | 1.000 |
| cql | price_spike_low_renewable | 6.440 | 6.440 | 92823.102 | 1.000 |
| cql | shoulder_season | 0.000 | 0.000 | 21292.709 | 0.000 |
| cql | summer_peak | 0.000 | 0.000 | 22014.367 | 0.000 |
| cql | three_day_low_renewable | 51.374 | 51.374 | 438024.510 | 1.000 |
| cql | warm_low_solar_zone | 0.000 | 0.000 | 23620.396 | 0.000 |
| cql | year_2017_winter | 51.970 | 51.970 | 443649.500 | 1.000 |
| cql | year_2018_winter | 26.603 | 26.603 | 232912.885 | 1.000 |
| cql | year_2019_winter | 5.589 | 5.589 | 65580.065 | 1.000 |
| cql_adaptive_safety | cold_climate_zone | 0.000 | 0.000 | 24462.210 | 0.000 |
| cql_adaptive_safety | cold_wave_device_fault | 0.000 | 0.000 | 32847.613 | 0.000 |
| cql_adaptive_safety | cold_wave_extreme | 0.000 | 0.000 | 16563.222 | 0.000 |
| cql_adaptive_safety | compound_extreme | 0.000 | 0.000 | 25173.275 | 0.000 |
| cql_adaptive_safety | in_distribution | 0.000 | 0.000 | 14050.049 | 0.000 |
| cql_adaptive_safety | load_up_20 | 0.000 | 0.000 | 17546.930 | 0.000 |
| cql_adaptive_safety | price_spike_low_renewable | 0.000 | 0.000 | 42448.064 | 0.000 |
| cql_adaptive_safety | shoulder_season | 0.000 | 0.000 | 21292.709 | 0.000 |
| cql_adaptive_safety | summer_peak | 0.000 | 0.000 | 22014.367 | 0.000 |
| cql_adaptive_safety | three_day_low_renewable | 0.000 | 0.000 | 30123.663 | 0.000 |
| cql_adaptive_safety | warm_low_solar_zone | 0.000 | 0.000 | 23620.396 | 0.000 |
| cql_adaptive_safety | year_2017_winter | 0.000 | 0.000 | 30349.127 | 0.000 |
| cql_adaptive_safety | year_2018_winter | 0.000 | 0.000 | 21288.022 | 0.000 |
| cql_adaptive_safety | year_2019_winter | 0.000 | 0.000 | 21220.868 | 0.000 |
| cql_fixed_safety | cold_wave_extreme | 0.000 | 0.000 | 16976.645 | 0.000 |
| cql_fixed_safety | compound_extreme | 0.000 | 0.000 | 25649.354 | 0.000 |
| cql_fixed_safety | in_distribution | 0.000 | 0.000 | 14233.470 | 0.000 |
| cql_fixed_safety | load_up_20 | 0.000 | 0.000 | 18361.253 | 0.000 |
| cql_ood_warning | cold_wave_extreme | 58.799 | 58.799 | 485180.391 | 1.000 |
| cql_ood_warning | compound_extreme | 73.296 | 73.296 | 608418.665 | 1.000 |
| cql_ood_warning | in_distribution | 2.373 | 2.373 | 32887.371 | 0.800 |
| cql_ood_warning | load_up_20 | 20.086 | 20.086 | 177352.991 | 1.000 |
| iql | cold_climate_zone | 63.740 | 63.740 | 531182.470 | 1.000 |
| iql | cold_wave_device_fault | 117.076 | 117.076 | 964072.074 | 1.000 |
| iql | cold_wave_extreme | 79.167 | 79.167 | 647069.910 | 1.000 |
| iql | compound_extreme | 96.659 | 96.659 | 794232.809 | 1.000 |
| iql | in_distribution | 12.560 | 12.560 | 113221.260 | 0.800 |
| iql | load_up_20 | 38.772 | 38.772 | 325985.842 | 1.000 |
| iql | price_spike_low_renewable | 11.328 | 11.328 | 131464.685 | 1.000 |
| iql | shoulder_season | 0.000 | 0.000 | 21382.132 | 0.000 |
| iql | summer_peak | 0.000 | 0.000 | 22128.811 | 0.000 |
| iql | three_day_low_renewable | 59.340 | 59.340 | 501135.623 | 1.000 |
| iql | warm_low_solar_zone | 0.000 | 0.000 | 23704.604 | 0.000 |
| iql | year_2017_winter | 60.102 | 60.102 | 508054.354 | 1.000 |
| iql | year_2018_winter | 32.111 | 32.111 | 276428.882 | 1.000 |
| iql | year_2019_winter | 9.979 | 9.979 | 100180.478 | 1.000 |
| iql_adaptive_safety | cold_climate_zone | 0.000 | 0.000 | 24312.025 | 0.000 |
| iql_adaptive_safety | cold_wave_device_fault | 0.000 | 0.000 | 32515.716 | 0.000 |
| iql_adaptive_safety | cold_wave_extreme | 0.000 | 0.000 | 17639.833 | 0.000 |
| iql_adaptive_safety | compound_extreme | 0.000 | 0.000 | 25010.747 | 0.000 |
| iql_adaptive_safety | in_distribution | 0.000 | 0.000 | 14423.177 | 0.000 |
| iql_adaptive_safety | load_up_20 | 0.000 | 0.000 | 17940.807 | 0.000 |

## 可复现命令

- `python scripts\run_week13_14_experiments.py`
- `python scripts\run_week15_16_experiments.py`
- `python -m unittest discover -s tests -v`

注册表：`docs/experiment_registry.md`
