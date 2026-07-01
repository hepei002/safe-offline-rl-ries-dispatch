import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const report = JSON.parse(
  await fs.readFile("data/processed/metadata/quality_report_2017_2019.json", "utf8"),
);
const outputDir = "outputs/data";
await fs.mkdir(outputDir, { recursive: true });

const sources = [
  [
    "OPSD Time Series",
    "2020-10-06",
    "2026-06-25",
    "来源特定条款；按OPSD README署名，并注明ENTSO-E等原始来源",
    "https://doi.org/10.25832/time_series/2020-10-06",
    "data/raw/opsd/time_series_60min_singleindex.csv",
    report.raw_files[0].bytes,
    report.raw_files[0].sha256,
    "负荷、光伏和风电实际出力",
  ],
  [
    "OPSD Weather Data",
    "2020-09-16",
    "2026-06-25",
    "来源特定条款；按OPSD README署名，并遵守MERRA-2/Renewables.ninja来源要求",
    "https://doi.org/10.25832/weather_data/2020-09-16",
    "data/raw/opsd_weather/weather_data.csv",
    report.raw_files[1].bytes,
    report.raw_files[1].sha256,
    "德国人口加权温度、直接与散射太阳辐射",
  ],
  [
    "When2Heat",
    "2023-07-27",
    "2026-06-25",
    "数据CC BY 4.0；脚本MIT",
    "https://doi.org/10.25832/when2heat/2023-07-27",
    "data/raw/when2heat/when2heat.csv",
    report.raw_files[2].bytes,
    report.raw_files[2].sha256,
    "标准化热需求曲线和空气源热泵COP",
  ],
];

const variables = [
  ["utc_timestamp","datetime UTC","ISO 8601","联合","唯一连续UTC小时索引"],
  ["electric_load_actual_mw","MW","数值","OPSD","德国实际总负荷"],
  ["solar_generation_actual_mw","MW","数值","OPSD","德国实际光伏发电"],
  ["wind_generation_actual_mw","MW","数值","OPSD","德国实际风电总出力"],
  ["wind_offshore_generation_actual_mw","MW","数值","OPSD","德国实际海上风电"],
  ["wind_onshore_generation_actual_mw","MW","数值","OPSD","德国实际陆上风电"],
  ["temperature_c","°C","数值","OPSD Weather","德国人口加权气温"],
  ["radiation_direct_horizontal_w_m2","W/m²","数值","OPSD Weather","直接水平辐射"],
  ["radiation_diffuse_horizontal_w_m2","W/m²","数值","OPSD Weather","散射水平辐射"],
  ["radiation_global_horizontal_w_m2","W/m²","数值","派生","直接与散射水平辐射之和"],
  ["cop_ashp_floor","—","数值","When2Heat","空气源热泵地板供暖COP"],
  ["cop_ashp_radiator","—","数值","When2Heat","空气源热泵散热器供暖COP"],
  ["cop_ashp_water","—","数值","When2Heat","空气源热泵热水COP"],
  ["heat_profile_space_com_mw_per_twh","MW/TWh","数值","When2Heat","商业建筑空间供热标准化曲线"],
  ["heat_profile_space_mfh_mw_per_twh","MW/TWh","数值","When2Heat","多户住宅空间供热标准化曲线"],
  ["heat_profile_space_sfh_mw_per_twh","MW/TWh","数值","When2Heat","独立住宅空间供热标准化曲线"],
  ["heat_profile_water_com_mw_per_twh","MW/TWh","数值","When2Heat","商业建筑热水标准化曲线"],
  ["heat_profile_water_mfh_mw_per_twh","MW/TWh","数值","When2Heat","多户住宅热水标准化曲线"],
  ["heat_profile_water_sfh_mw_per_twh","MW/TWh","数值","When2Heat","独立住宅热水标准化曲线"],
  ["heat_demand_reference_2015_mw","MW","数值","派生","用2015年度TWh权重缩放的合成热负荷；非实测"],
  ["imputed_opsd","布尔","TRUE/FALSE","质量标记","OPSD字段是否插值"],
  ["imputed_weather","布尔","TRUE/FALSE","质量标记","天气字段是否插值"],
  ["imputed_when2heat","布尔","TRUE/FALSE","质量标记","When2Heat字段是否插值"],
  ["imputed_any","布尔","TRUE/FALSE","质量标记","本小时是否存在任何插值"],
];

const steps = [
  [1,"原始数据冻结","文件保存在data/raw，不手工修改","保留原始CSV及README；计算SHA-256"],
  [2,"选择德国字段","只读入研究所需列","减少内存并避免混入其他国家数据"],
  [3,"格式解析","OPSD用逗号；When2Heat用分号和逗号小数点","避免When2Heat被错误拆列"],
  [4,"UTC解析","解析utc_timestamp为带时区UTC时间","不使用CET/CEST作为主索引"],
  [5,"重复处理","相同时间戳数值取均值","本批数据重复数为0"],
  [6,"完整索引","重建2017-01-01至2019-12-31小时索引","预期26,280行"],
  [7,"缺失处理","仅内部1小时缺口时间线性插值","长缺口直接报错"],
  [8,"夏令时修复","补When2Heat秋季DST缺失小时","每年1行，共3行"],
  [9,"热负荷换算","用2015六类年度TWh权重乘标准化曲线","输出2015基准规模合成热负荷"],
  [10,"辐射派生","直接水平辐射+散射水平辐射","生成全球水平辐射"],
  [11,"联合与验收","按UTC内连接并检查缺失、重复和行数","输出CSV与JSON质量报告"],
];

const missing = [
  ["2017-10-29T01:00:00Z","When2Heat","9个COP/热曲线字段","秋季夏令时转换导致UTC小时缺失","相邻小时线性插值","imputed_when2heat=TRUE"],
  ["2018-10-28T01:00:00Z","When2Heat","9个COP/热曲线字段","秋季夏令时转换导致UTC小时缺失","相邻小时线性插值","imputed_when2heat=TRUE"],
  ["2019-10-27T01:00:00Z","When2Heat","9个COP/热曲线字段","秋季夏令时转换导致UTC小时缺失","相邻小时线性插值","imputed_when2heat=TRUE"],
];

const omitted = [
  ["DE_LU_price_day_ahead","2017全部缺失、2018仅部分覆盖","不纳入联合表","后续单独补充市场价格或构造透明的分时电价场景"],
  ["DE_load_forecast_entsoe_transparency","2018连续约24小时缺口","不纳入联合表","后续建立独立预测模块并显式控制预测误差"],
];

const wb = Workbook.create();
const summary = wb.worksheets.add("概览");
const sourceSheet = wb.worksheets.add("数据来源");
const variableSheet = wb.worksheets.add("变量字典");
const processSheet = wb.worksheets.add("处理步骤");
const qualitySheet = wb.worksheets.add("质量检查");
const missingSheet = wb.worksheets.add("缺失与排除");

for (const sheet of [summary, sourceSheet, variableSheet, processSheet, qualitySheet, missingSheet]) {
  sheet.showGridLines = false;
}

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["德国电–热联合小时数据台账"]];
summary.getRange("A1:H1").format = { fill:"#17365D", font:{bold:true,color:"#FFFFFF",size:16} };
summary.getRange("A3:B10").values = [
  ["指标","结果"],
  ["UTC起点",report.period.start_utc],
  ["UTC终点",report.period.end_utc],
  ["小时行数",report.period.rows],
  ["重复时间戳",0],
  ["最终缺失单元格",0],
  ["存在插值的小时",report.when2heat.imputed_rows],
  ["输出SHA-256",report.output.sha256],
];
summary.getRange("A3:B3").format = { fill:"#2F75B5", font:{bold:true,color:"#FFFFFF"} };
summary.getRange("A3:B10").format.borders = { preset:"outside", style:"thin", color:"#A6A6A6" };
summary.getRange("B4:B5").format.numberFormat = "yyyy-mm-dd hh:mm";
summary.getRange("A12:H12").merge();
summary.getRange("A12").values = [["结论：2017–2019形成26,280个连续UTC小时；仅When2Heat三个DST小时被插值，所有插值均有布尔标记。"]];
summary.getRange("A12:H12").format = { fill:"#E2F0D9", font:{bold:true,color:"#375623"}, wrapText:true };
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 70;
summary.getRange("C:H").format.columnWidth = 16;

sourceSheet.getRange("A1:I1").values = [["数据源","版本","下载日期","许可与署名","官方地址","本地文件","字节数","SHA-256","用途"]];
sourceSheet.getRange("A2:I4").values = sources;
const sourceTable = sourceSheet.tables.add("A1:I4",true,"SourceRegister");
sourceTable.style = "TableStyleMedium2";
sourceSheet.freezePanes.freezeRows(1);
sourceSheet.getRange("A1:I4").format.wrapText = true;
sourceSheet.getRange("A:A").format.columnWidth=24;
sourceSheet.getRange("B:C").format.columnWidth=14;
sourceSheet.getRange("D:D").format.columnWidth=42;
sourceSheet.getRange("E:F").format.columnWidth=48;
sourceSheet.getRange("G:G").format.columnWidth=15;
sourceSheet.getRange("H:H").format.columnWidth=68;
sourceSheet.getRange("I:I").format.columnWidth=34;
sourceSheet.getRange("G2:G4").format.numberFormat="#,##0";

variableSheet.getRange("A1:E1").values = [["变量","单位","类型","来源","定义/说明"]];
variableSheet.getRange(`A2:E${variables.length+1}`).values = variables;
const variableTable=variableSheet.tables.add(`A1:E${variables.length+1}`,true,"VariableDictionary");
variableTable.style="TableStyleMedium2";
variableSheet.freezePanes.freezeRows(1);
variableSheet.getRange(`A1:E${variables.length+1}`).format.wrapText=true;
variableSheet.getRange("A:A").format.columnWidth=44;
variableSheet.getRange("B:C").format.columnWidth=16;
variableSheet.getRange("D:D").format.columnWidth=22;
variableSheet.getRange("E:E").format.columnWidth=52;

processSheet.getRange("A1:D1").values=[["序号","处理环节","规则","审计说明"]];
processSheet.getRange(`A2:D${steps.length+1}`).values=steps;
const processTable=processSheet.tables.add(`A1:D${steps.length+1}`,true,"ProcessingLog");
processTable.style="TableStyleMedium2";
processSheet.freezePanes.freezeRows(1);
processSheet.getRange(`A1:D${steps.length+1}`).format.wrapText=true;
processSheet.getRange("A:A").format.columnWidth=8;
processSheet.getRange("B:B").format.columnWidth=26;
processSheet.getRange("C:D").format.columnWidth=48;

qualitySheet.getRange("A1:E1").values=[["数据块","重复行","插值单元格","插值小时","验收"]];
qualitySheet.getRange("A2:E5").values=[
  ["OPSD",report.opsd.duplicate_rows,report.opsd.imputed_cells,report.opsd.imputed_rows,"通过"],
  ["OPSD Weather",report.weather.duplicate_rows,report.weather.imputed_cells,report.weather.imputed_rows,"通过"],
  ["When2Heat",report.when2heat.duplicate_rows,report.when2heat.imputed_cells,report.when2heat.imputed_rows,"通过（仅DST短缺口）"],
  ["联合表",0,0,report.when2heat.imputed_rows,"通过：无最终缺失或重复"],
];
const qualityTable=qualitySheet.tables.add("A1:E5",true,"QualitySummary");
qualityTable.style="TableStyleMedium2";
qualitySheet.getRange("A:E").format.columnWidth=25;
qualitySheet.getRange("E:E").format.columnWidth=38;
qualitySheet.getRange("A1:E5").format.wrapText=true;
qualitySheet.getRange("A8:C8").values=[["2015基准热需求类别","年度TWh","用途"]];
const heatEntries=Object.entries(report.heat_reference_annual_twh).filter(([key])=>key!=="total");
qualitySheet.getRange(`A9:C${8+heatEntries.length}`).values=heatEntries.map(([key,value])=>[key,value,"缩放对应MW/TWh标准化曲线"]);
qualitySheet.getRange(`A9:C${8+heatEntries.length}`).format.wrapText=true;
qualitySheet.getRange(`B9:B${8+heatEntries.length}`).format.numberFormat="0.000";
qualitySheet.getRange("A:A").format.columnWidth=46;

missingSheet.getRange("A1:F1").values=[["UTC时间","数据源","受影响字段","原因","处理","标记"]];
missingSheet.getRange("A2:F4").values=missing;
const missingTable=missingSheet.tables.add("A1:F4",true,"ImputationLog");
missingTable.style="TableStyleMedium2";
missingSheet.getRange("A7:D7").values=[["排除字段","原因","处理决定","后续方案"]];
missingSheet.getRange("A8:D9").values=omitted;
const omittedTable=missingSheet.tables.add("A7:D9",true,"ExcludedVariables");
omittedTable.style="TableStyleMedium4";
missingSheet.getRange("A:F").format.columnWidth=32;
missingSheet.getRange("C:E").format.columnWidth=48;
missingSheet.getRange("A1:F9").format.wrapText=true;
missingSheet.getRange("A2:A4").format.numberFormat="yyyy-mm-dd hh:mm";

const inspection = await wb.inspect({
  kind:"table",
  range:"概览!A1:H12",
  include:"values,formulas",
  tableMaxRows:15,
  tableMaxCols:10,
});
console.log(inspection.ndjson);
const errors = await wb.inspect({
  kind:"match",
  searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options:{useRegex:true,maxResults:100},
  summary:"formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of ["概览","数据来源","变量字典","处理步骤","质量检查","缺失与排除"]) {
  const preview=await wb.render({sheetName,autoCrop:"all",scale:1,format:"png"});
  await fs.writeFile(`${outputDir}/${sheetName}.png`,new Uint8Array(await preview.arrayBuffer()));
}

const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(`${outputDir}/德国电热联合数据_来源与处理台账.xlsx`);
