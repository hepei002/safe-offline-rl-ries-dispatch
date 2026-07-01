# OPSD电力时序、OPSD天气与When2Heat数据下载指南

## 1. Open Power System Data：电负荷、风光出力与日前电价

数据主页：

- https://data.open-power-system-data.org/time_series/latest/

本研究推荐下载：

- 小时级单表CSV：  
  https://data.open-power-system-data.org/time_series/latest/time_series_60min_singleindex.csv
- Excel版本：  
  https://data.open-power-system-data.org/time_series/latest/time_series.xlsx
- 完整版本压缩包：  
  https://data.open-power-system-data.org/time_series/opsd-time-series-2020-10-06.zip
- 字段说明：  
  https://data.open-power-system-data.org/time_series/latest/README.md
- 数据包元数据：  
  https://data.open-power-system-data.org/time_series/latest/datapackage.json

建议优先下载 `time_series_60min_singleindex.csv`、`README.md` 和
`datapackage.json`。当前 `latest` 指向2020-10-06版本。论文中应记录具体版本，
不能只写“latest”。

德国主案例拟使用的字段包括：

- `DE_load_actual_entsoe_transparency`
- `DE_load_forecast_entsoe_transparency`
- 德国风电与光伏实际出力字段
- 德国日前电价字段

具体字段名以下载版本的 `README.md` 和 `datapackage.json` 为准。

## 2. When2Heat：热负荷与热泵COP

数据主页：

- https://data.open-power-system-data.org/when2heat/latest/

本研究推荐下载：

- CSV版本：  
  https://data.open-power-system-data.org/when2heat/latest/when2heat.csv
- Excel版本：  
  https://data.open-power-system-data.org/when2heat/latest/when2heat.xlsx
- 完整版本压缩包：  
  https://data.open-power-system-data.org/when2heat/opsd-when2heat-2023-07-27.zip
- 字段说明：  
  https://data.open-power-system-data.org/when2heat/latest/README.md
- 数据包元数据：  
  https://data.open-power-system-data.org/when2heat/latest/datapackage.json

当前 `latest` 指向2023-07-27版本。该数据覆盖多个欧洲国家的小时级空间供热、
热水负荷和热泵COP。德国主案例优先选择：

- Germany；
- residential space heating；
- commercial space heating；
- hot water；
- air-source heat-pump COP。

具体列名以 `README.md` 为准。

## 3. OPSD Weather Data：气温与太阳辐射

数据主页：

- https://data.open-power-system-data.org/weather_data/latest/

本研究推荐下载：

- CSV版本：  
  https://data.open-power-system-data.org/weather_data/latest/weather_data.csv
- 完整版本压缩包：  
  https://data.open-power-system-data.org/weather_data/opsd-weather_data-2020-09-16.zip
- 字段说明：  
  https://data.open-power-system-data.org/weather_data/latest/README.md
- 数据包元数据：  
  https://data.open-power-system-data.org/weather_data/latest/datapackage.json

德国主案例使用：

- `DE_temperature`
- `DE_radiation_direct_horizontal`
- `DE_radiation_diffuse_horizontal`

该数据为欧洲国家级、人口加权的小时气象时序，来源于NASA MERRA-2并由
Renewables.ninja聚合。当前版本为2020-09-16，数据覆盖至2019年。

风电不从风速重建，而直接使用OPSD的德国实际风电出力。热泵COP直接使用
When2Heat，因此第一版实验不再要求ERA5。

## 4. ERA5：可选扩展数据

数据产品页：

- https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels

CDS API配置说明：

- https://cds.climate.copernicus.eu/how-to-api

数据集DOI：

- https://doi.org/10.24381/cds.adbb2d47

ERA5不再作为第一版实验的必需数据。只有在需要城市级天气、跨地区空间泛化或
2020年以后气象数据时再使用。ERA5不能通过一个固定CSV链接直接下载，需要：

1. 注册并登录Copernicus Climate Data Store；
2. 在数据产品页面接受许可；
3. 在“Download”页选择变量、年份、月份、日期、小时和区域；
4. 手工下载NetCDF/GRIB，或者点击“Show API request code”获得Python脚本。

如后续扩展，建议下载：

- `2m_temperature`
- `10m_u_component_of_wind`
- `10m_v_component_of_wind`
- `surface_solar_radiation_downwards`
- 可选：`total_cloud_cover`

推荐设置：

- Product type：Reanalysis
- Temporal resolution：Hourly
- Data format：NetCDF
- 区域：德国边界或主案例城市周边小区域
- 年份：先下载与OPSD和When2Heat具有交集的年份

第一版研究建议采用2015–2017年训练、2018年验证、2019年时间外测试。最终划分
仍需在检查OPSD电力、OPSD天气与When2Heat的实际重叠范围后确定。

## 5. 下载后的目录建议

```text
data/raw/
├── opsd/
│   ├── time_series_60min_singleindex.csv
│   ├── README.md
│   └── datapackage.json
├── opsd_weather/
│   ├── weather_data.csv
│   ├── README.md
│   └── datapackage.json
└── when2heat/
│   ├── when2heat.csv
│   ├── README.md
│   └── datapackage.json
```

原始文件不要手工修改。后续所有单位转换、UTC时间对齐、缺失值处理和园区尺度
缩放均通过脚本写入 `data/interim/` 和 `data/processed/`。
