# Data directory

数据按“原始数据 → 中间处理 → 最终建模数据 → 离线 RL 轨迹”组织。

本仓库的开源策略是：保留可复现的小型派生数据、质量报告和元数据；不直接提交第三方原始大文件和中间处理文件。第三方原始数据请按 `docs/data_download_guide.md` 和 `docs/data_provenance.md` 从官方来源下载。

```text
data/
├── raw/                 # ignored except README/datapackage metadata
│   ├── opsd/
│   ├── when2heat/
│   └── opsd_weather/
├── interim/             # ignored; regenerated from raw data
│   ├── opsd/
│   ├── when2heat/
│   ├── opsd_weather/
│   └── aligned/
├── processed/           # small derived benchmark data intended for reproducibility
│   ├── exogenous/
│   ├── metadata/
│   ├── scenarios/
│   ├── splits/
│   └── offline/
│       ├── expert.parquet
│       ├── mixed.parquet
│       ├── poor.parquet
│       └── metadata.yaml
└── README.md
```

## 使用规则

- `raw/`：保存官方下载文件，不手工修改或覆盖。
- `raw/opsd/`：保存 OPSD 电负荷、价格和风光出力时序。
- `raw/opsd_weather/`：保存 OPSD 温度和太阳辐射时序。
- `raw/when2heat/`：保存热负荷和热泵COP时序。
- `interim/`：保存解压、字段筛选、单位转换和单源清洗结果。
- `interim/aligned/`：保存完成 UTC 时间对齐但尚未形成实验划分的数据。
- `processed/exogenous/`：保存可直接输入能源系统模型的联合外生时序。
- `processed/metadata/`：保存质量报告、校验和与机器可读处理记录。
- `processed/scenarios/`：保存分布漂移和极端事件场景。
- `processed/splits/`：保存训练、验证、分布内测试和分布外测试索引。
- `processed/offline/`：保存由 MPC、规则控制和扰动策略生成的离线 RL 轨迹。
- 每个数据集应记录下载日期、版本、来源URL、许可证和处理脚本。

详细下载说明见 `docs/data_download_guide.md`。

## GitHub 提交边界

建议提交：

- `data/README.md`
- `data/raw/**/README.md`
- `data/raw/**/datapackage.json`
- `data/processed/exogenous/germany_joint_hourly_2017_2019.csv`
- `data/processed/metadata/quality_report_2017_2019.json`
- `data/processed/offline/*.parquet`
- `data/processed/offline/metadata.yaml`

不建议提交：

- `data/raw/**/*.csv`
- `data/raw/**/*.zip`
- `data/interim/**`

原因：原始数据体积较大且带有第三方许可/署名要求；中间数据可以由处理脚本再生。
