# 数据来源与处理台账

## 数据版本

| 数据源 | 版本 | 下载日期 | 许可与署名 | 官方地址 |
|---|---|---|---|---|
| OPSD Time Series | 2020-10-06 | 2026-06-25 | 来源特定条款；论文需按OPSD README署名并注明原始ENTSO-E等来源 | https://doi.org/10.25832/time_series/2020-10-06 |
| OPSD Weather Data | 2020-09-16 | 2026-06-25 | 来源特定条款；按OPSD README署名，并遵守MERRA-2/Renewables.ninja来源要求 | https://doi.org/10.25832/weather_data/2020-09-16 |
| When2Heat | 2023-07-27 | 2026-06-25 | 数据：CC BY 4.0；脚本：MIT | https://doi.org/10.25832/when2heat/2023-07-27 |

下载日期记录为本项目确认文件已放入 `data/raw/` 的日期。原始HTTP响应时间未单独保存。

## 处理窗口

- 开始：2017-01-01 00:00:00 UTC
- 结束：2019-12-31 23:00:00 UTC
- 频率：1小时
- 行数：26,280
- 时区：UTC

## 处理步骤

1. 原始文件保存在 `data/raw/`，不覆盖、不手工修改。
2. 仅读取德国相关字段。
3. OPSD和天气CSV按逗号分隔读取；When2Heat按分号分隔、逗号小数点读取。
4. 所有 `utc_timestamp` 解析为带时区的UTC时间。
5. 若存在重复时间戳，数值字段取均值；本批原始数据未发现重复时间戳。
6. 重建2017–2019完整UTC小时索引，不使用本地CET/CEST索引。
7. 仅允许对内部连续1小时缺口做时间线性插值；更长缺口直接报错。
8. When2Heat在每年秋季夏令时切换点缺少一个UTC小时，已插值：
   - 2017-10-29 01:00:00 UTC
   - 2018-10-28 01:00:00 UTC
   - 2019-10-27 01:00:00 UTC
9. 使用2015年德国六类建筑热需求计算年度TWh权重，将2017–2019标准化热曲线换算为
   `heat_demand_reference_2015_mw`。该变量是2015基准规模的合成热负荷，不是实测值。
10. 全球水平辐射由直接水平辐射与散射水平辐射相加得到。
11. 合并后检查时间连续性、重复时间戳、缺失值和预期行数。

## 未纳入字段

- `DE_LU_price_day_ahead`：2017年全部缺失，2018年仅部分覆盖，不能构成完整三年公共窗口。
- `DE_load_forecast_entsoe_transparency`：2018年存在连续约24小时缺口，超过1小时插值上限。

价格和预测误差应在后续实验中作为独立输入或预测模块处理，不能通过长缺口插值伪造。

## 输出

- 联合表：`data/processed/exogenous/germany_joint_hourly_2017_2019.csv`
- 对齐副本：`data/interim/aligned/germany_joint_hourly_2017_2019.csv`
- 质量报告：`data/processed/metadata/quality_report_2017_2019.json`
- 数据处理脚本：`src/data/build_joint_dataset.py`
- 自动测试：`tests/test_build_joint_dataset.py`
