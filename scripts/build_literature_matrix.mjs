import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/literature";
await fs.mkdir(outputDir, { recursive: true });

const papers = [
  [1,"综合能源系统+安全RL","核心",2025,"Safe-AutoSAC: AutoML-enhanced safe deep reinforcement learning for integrated energy system scheduling with multi-channel informer forecasting and electric vehicle demand response","Yang Li; Bingsong Zhao; Yuanzheng Li; Chao Long; Sen Li; Zhaoyang Dong; Mohammad Shahidehpour","Applied Energy","https://doi.org/10.1016/j.apenergy.2025.126468","综合能源系统、预测与电动汽车需求响应","安全SAC、AutoML、Informer预测","可再生能源、负荷和预测误差","安全强化学习约束机制","仿真综合能源系统","直接相邻工作；用于界定普通安全DRL已经覆盖的能力","不是离线RL；分布漂移和历史数据支持度不是核心","待读全文"],
  [2,"综合能源系统+鲁棒优化","核心",2025,"Stochastic robust optimization scheduling for integrated energy system cluster based on data-driven method","Xun Xu; Zhenguo Shao; Feixiong Chen; Guoyang Cheng","Applied Energy","https://doi.org/10.1016/j.apenergy.2025.126512","综合能源系统集群","数据驱动随机-鲁棒优化","多源不确定性","优化可行域与鲁棒约束","数据驱动场景/仿真系统","构成最重要的优化类强基线","在线滚动计算和策略快速推断不是重点","待读全文"],
  [3,"综合能源系统+风险调度","核心",2025,"Optimal scheduling of park-level integrated energy system considering multiple uncertainties: A comprehensive risk strategy-information gap decision theory method","Zhengxiong Ji; Jianyan Tian; Shuwei Liu; Lizhi Yang; Yuanyuan Dai; Amit Banerjee","Applied Energy","https://doi.org/10.1016/j.apenergy.2024.124700","园区级综合能源系统","信息间隙决策理论与综合风险策略","多重不确定性","风险约束/鲁棒决策","园区仿真案例","说明风险调度已经拥挤；用于比较尾部风险描述","不学习快速策略；不处理离线数据分布外动作","待读全文"],
  [4,"多能系统+物理安全RL","核心",2023,"Secure energy management of multi-energy microgrid: A physical-informed safe reinforcement learning approach","Yi Wang; Dawei Qiu; Mingyang Sun; Goran Strbac; Zhiwei Gao","Applied Energy","https://doi.org/10.1016/j.apenergy.2023.120759","多能源微电网","物理信息安全强化学习","运行不确定性与安全风险","物理知识嵌入和安全控制","仿真多能源微电网","最直接的物理安全RL相邻工作","在线/交互式训练；未聚焦离线分布漂移","待读全文"],
  [5,"多能系统+硬约束RL","核心",2023,"Safe reinforcement learning for multi-energy management systems with known constraint functions","Glenn Ceusters; Luis Ramirez Camargo; Rüdiger Franke; Ann Nowé; Maarten Messagie","Energy and AI","https://doi.org/10.1016/j.egyai.2022.100227","多能源管理系统","SafeFallback与GiveSafe","训练探索和部署动作风险","已知约束函数的硬约束处理","仿真多能源系统","安全层和回退机制的重要比较对象","不以离线RL和OOD漂移为主；约束函数需已知","待读全文"],
  [6,"建筑能源+安全RL","高",2025,"Safe deep reinforcement learning for building energy management","Xiangwei Wang; Peng Wang; Renke Huang; Xiuli Zhu; Javier Arroyo; Ning Li","Applied Energy","https://doi.org/10.1016/j.apenergy.2024.124328","建筑能源管理","安全深度强化学习","建筑负荷和运行变化","安全策略/约束处理","建筑仿真环境","提供建筑侧安全RL强基线与评价指标","对象偏建筑；非区域电热系统和离线漂移","待读全文"],
  [7,"配电网+氢能+安全RL","高",2024,"Safe deep reinforcement learning-assisted two-stage energy management for active power distribution networks with hydrogen fueling stations","Panggah Prabawa; Dae-Hyun Choi","Applied Energy","https://doi.org/10.1016/j.apenergy.2024.124170","主动配电网与加氢站","两阶段安全DRL","可再生能源和需求不确定性","两阶段安全控制","仿真配电系统","说明安全DRL在能源网络中的最新应用边界","系统对象不同；不研究离线数据支持和OOD检测","待读全文"],
  [8,"离线RL+HVAC","核心",2022,"Data-driven Offline Reinforcement Learning for HVAC-systems","Christian Blad; Simon Bøgh; Carsten Skovmose Kallesøe","Energy","https://doi.org/10.1016/j.energy.2022.125290","HVAC系统","数据驱动离线强化学习","固定历史数据和环境变化","未强调硬物理投影","HVAC数据/仿真","能源领域离线RL直接先例","单一HVAC对象；分布漂移与多能耦合不足","待读全文"],
  [9,"离线RL+热能管理","核心",2022,"Comparison of online and offline deep reinforcement learning with model predictive control for thermal energy management","Silvio Brandi; Massimo Fiorentini; Alfonso Capozzoli","Automation in Construction","https://doi.org/10.1016/j.autcon.2022.104128","建筑热能管理","在线/离线DRL与MPC比较","天气和负荷变化","MPC物理约束","建筑热环境","支持离线RL与MPC的公平对比设计","未形成OOD感知安全框架","待读全文"],
  [10,"多能源+随机优化","高",2020,"Day-ahead stochastic scheduling of integrated multi-energy system for flexibility synergy and uncertainty balancing","Ana Turk; Qiuwei Wu; Menglin Zhang; Jacob Østergaard","Energy","https://doi.org/10.1016/j.energy.2020.117130","综合多能源系统","日前随机调度","多源不确定性","随机场景与系统约束","综合能源仿真系统","随机优化基线和不确定性建模参考","计算型优化；不利用离线策略推断","待读全文"],
  [11,"区域综合能源系统","高",2022,"Multi-energy coupling analysis and optimal scheduling of regional integrated energy system","Jianhui Wang; Jiangwei Mao; Ruhai Hao; Shoudong Li; Guangqing Bao","Energy","https://doi.org/10.1016/j.energy.2022.124482","区域综合能源系统","多能耦合分析与优化调度","常规运行变化","显式系统约束","区域能源仿真","用于确定电热系统模型、目标和设备耦合关系","智能策略、离线学习和漂移均非核心","待读全文"],
  [12,"区域综合能源系统+不确定性","高",2022,"Optimal scheduling strategy of a regional integrated energy system considering renewable energy uncertainty and heat network transmission characteristics","Haipeng Chen; Lin Gao; Yongling Zhang; Chang Zhao","Energy Reports","https://doi.org/10.1016/j.egyr.2022.05.235","区域电热综合能源系统","不确定性优化调度","可再生能源不确定性","热网传输和运行约束","区域电热仿真","电热系统建模和不确定性场景参考","不处理数据驱动策略部署和分布外失效","待读全文"],
  [13,"开源环境","高",2020,"CityLearn: Standardizing Research in Multi-Agent Reinforcement Learning for Demand Response and Urban Energy Management","José R. Vázquez-Canteli; Sourav Dey; Gregor Henze; Zoltán Nagy","arXiv / CityLearn","https://arxiv.org/abs/2012.10504","城市建筑群与需求响应","标准化Gym强化学习环境","气象、负荷和建筑差异","环境内设备约束","CityLearn公开环境","环境接口、基准协议和建筑侧数据参考","缺少CHP等区域多能设备；需扩展为电热系统","摘要已核验"],
  [14,"开放数据","高",2019,"Open Power System Data - Frictionless data for electricity system modelling","Frauke Wiese; Ingmar Schlecht; Wolf-Dieter Bunke; Clemens Gerbaulet; Lion Hirth; et al.","Applied Energy","https://arxiv.org/abs/1812.10405","欧洲电力系统数据","开放数据处理与可复现数据包","跨来源数据质量差异","数据校验与溯源","OPSD","支撑电负荷、价格和风光数据来源说明","国家级数据需缩放，不能称为真实园区测量","摘要已核验"],
  [15,"开放热负荷数据","核心",2019,"Time series of heat demand and heat pump efficiency for energy system modeling","Oliver Ruhnau; Lion Hirth; Aaron Praktiknjo","Scientific Data","https://doi.org/10.1038/s41597-019-0199-y","欧洲热需求与热泵","热负荷和COP时序生成","气温和建筑类型差异","数据模型中的物理关系","When2Heat","核心热负荷和COP数据依据","数据为模型化时序而非园区设备实测控制记录","摘要已核验"],
  [16,"能源系统工具","高",2018,"PyPSA: Python for Power System Analysis","Thomas Brown; Jonas Hörsch; David Schlachtberger","Journal of Open Research Software","https://doi.org/10.5334/jors.188","电力与多能源耦合系统","多时段仿真和优化工具","可再生能源时序变化","显式网络和设备约束","PyPSA开源模型","可用于确定性优化、MPC和离线轨迹生成","需自行包装Gym环境和安全投影接口","摘要已核验"],
  [17,"离线RL算法","核心",2020,"Conservative Q-Learning for Offline Reinforcement Learning","Aviral Kumar; Aurick Zhou; George Tucker; Sergey Levine","NeurIPS","https://arxiv.org/abs/2006.04779","通用离线连续/离散控制","CQL保守价值估计","数据策略与学习策略分布偏移","价值下界式保守机制","D4RL等基准","核心离线RL强基线；直接针对OOD动作过估计","不保证能源物理可行性；保守系数可能敏感","摘要已核验"],
  [18,"离线RL算法","核心",2022,"Offline Reinforcement Learning with Implicit Q-Learning","Ilya Kostrikov; Ashvin Nair; Sergey Levine","ICLR","https://arxiv.org/abs/2110.06169","通用离线连续控制","IQL期望分位值函数与加权行为克隆","避免直接查询数据外动作","隐式策略约束","D4RL等基准","推荐主策略，稳定且较易实现","不显式建模安全成本和物理约束","摘要已核验"],
  [19,"离线RL算法","高",2021,"A Minimalist Approach to Offline Reinforcement Learning","Scott Fujimoto; Shixiang Shane Gu","NeurIPS","https://arxiv.org/abs/2106.06860","通用离线连续控制","TD3+BC","数据外价值误差","行为克隆正则","D4RL等基准","简单、强、适合作为公平基线","没有显式安全和漂移检测","摘要已核验"],
  [20,"离线安全RL","核心",2022,"COptiDICE: Offline Constrained Reinforcement Learning via Stationary Distribution Correction Estimation","Jongmin Lee; Cosmin Paduraru; Daniel J. Mankowitz; Nicolas Heess; Doina Precup; Kee-Eung Kim; Arthur Guez","ICLR / arXiv","https://arxiv.org/abs/2204.08957","通用离线约束决策","稳态分布修正估计","离线分布偏移和评价误差","成本保守的约束优化","离线约束RL基准","离线安全RL的重要算法比较对象","约束满足为期望成本层面；能源硬可行性仍需投影","摘要已核验"],
  [21,"离线RL数据协议","高",2020,"D4RL: Datasets for Deep Data-Driven Reinforcement Learning","Justin Fu; Aviral Kumar; Ofir Nachum; George Tucker; Sergey Levine","arXiv","https://arxiv.org/abs/2004.07219","通用离线RL数据集","多质量、多行为策略离线数据协议","数据覆盖与策略分布偏移","不专门处理安全","D4RL","指导Expert/Mixed/Poor数据集和统一评估协议","任务非能源系统，需要自行定义指标和约束成本","摘要已核验"],
  [22,"安全RL基础","高",2017,"Constrained Policy Optimization","Joshua Achiam; David Held; Aviv Tamar; Pieter Abbeel","ICML / PMLR","https://arxiv.org/abs/1705.10528","通用约束强化学习","CPO信赖域约束策略优化","在线采样条件下的不确定性","近似约束满足保证","连续控制基准","安全RL理论和约束MDP表述基础","在线算法；不适用于固定离线数据直接训练","摘要已核验"],
];

const resources = [
  ["OPSD time series","外生电力时序","负荷、日前价格、风光","2020-10-06","https://data.open-power-system-data.org/time_series/latest/time_series_60min_singleindex.csv","下载CSV、README和datapackage.json；记录具体版本"],
  ["When2Heat","外生热负荷时序","空间供热、热水、热泵COP","2023-07-27","https://data.open-power-system-data.org/when2heat/latest/when2heat.csv","优先选择德国小时级字段"],
  ["ERA5 single levels","气象再分析","2m气温、10m风、太阳辐射","持续更新","https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels","需注册、接受许可并按区域年份下载"],
  ["PyPSA","系统优化工具","电热系统、储能、MPC","持续更新","https://github.com/PyPSA/PyPSA","用于物理模型和轨迹生成"],
  ["CityLearn","RL环境参考","Gym接口、建筑能源和需求响应","持续更新","https://github.com/intelligent-environments-lab/CityLearn","参考接口，不直接替代区域电热模型"],
  ["d3rlpy","离线RL库","CQL、IQL、BC等","持续更新","https://github.com/takuseno/d3rlpy","快速跑通基线"],
  ["CORL","离线RL实现","单文件研究型实现","持续更新","https://github.com/corl-team/CORL","用于修改核心算法"],
  ["CVXPY","安全投影","凸优化与二次规划","持续更新","https://github.com/cvxpy/cvxpy","实现动作到物理可行域投影"],
  ["Minari","离线轨迹格式","标准化Gymnasium离线数据集","持续更新","https://github.com/Farama-Foundation/Minari","保存和发布离线轨迹"],
];

const workbook = Workbook.create();
const overview = workbook.worksheets.add("使用说明");
const matrix = workbook.worksheets.add("核心文献矩阵");
const tools = workbook.worksheets.add("数据与工具");

overview.showGridLines = false;
matrix.showGridLines = false;
tools.showGridLines = false;

overview.getRange("A1:H1").merge();
overview.getRange("A1").values = [["区域综合能源系统安全离线强化学习：文献矩阵"]];
overview.getRange("A1:H1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 16 },
  verticalAlignment: "center",
};
overview.getRange("A1:H1").format.rowHeight = 30;

overview.getRange("A3:B8").values = [
  ["项目","内容"],
  ["检索日期","2026-06-24"],
  ["目标期刊","Applied Energy"],
  ["核心文献数",papers.length],
  ["核心问题","离线策略在分布漂移下的性能与物理安全"],
  ["使用提示","先精读“核心”优先级，再补充被引与引用文献。内容列为摘要级初筛，不替代全文阅读。"],
];
overview.getRange("A3:B3").format = { fill: "#2F75B5", font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A3:B8").format.wrapText = true;
overview.getRange("A3:B8").format.borders = { preset: "outside", style: "thin", color: "#A6A6A6" };
overview.getRange("A10:H10").values = [["类别","论文数","建议阅读顺序","","论文论证环节","对应文献类型","",""]];
overview.getRange("A10:H10").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" } };
overview.getRange("A11:C16").values = [
  ["综合能源系统/安全RL",null,"先读直接相邻工作"],
  ["离线RL/离线安全RL",null,"再读算法基础"],
  ["优化与不确定性",null,"确定强基线"],
  ["数据与环境",null,"确认可复现性"],
  ["高优先级及以上",null,"前两周完成"],
  ["待读全文",null,"阅读后更新状态"],
];
overview.getRange("B11:B16").formulas = [
  ["=COUNTIF('核心文献矩阵'!$B$5:$B$100,\"综合能源系统+安全RL\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"多能系统+物理安全RL\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"多能系统+硬约束RL\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"建筑能源+安全RL\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"配电网+氢能+安全RL\")"],
  ["=COUNTIF('核心文献矩阵'!$B$5:$B$100,\"离线RL+HVAC\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"离线RL+热能管理\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"离线RL算法\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"离线安全RL\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"离线RL数据协议\")"],
  ["=COUNTIF('核心文献矩阵'!$B$5:$B$100,\"综合能源系统+鲁棒优化\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"多能源+随机优化\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"综合能源系统+风险调度\")"],
  ["=COUNTIF('核心文献矩阵'!$B$5:$B$100,\"开源环境\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"开放数据\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"开放热负荷数据\")+COUNTIF('核心文献矩阵'!$B$5:$B$100,\"能源系统工具\")"],
  ["=COUNTIF('核心文献矩阵'!$C$5:$C$100,\"核心\")+COUNTIF('核心文献矩阵'!$C$5:$C$100,\"高\")"],
  ["=COUNTIF('核心文献矩阵'!$P$5:$P$100,\"待读全文\")"],
];
overview.getRange("E11:H16").values = [
  ["研究必要性","综合能源风险调度、安全RL、离线RL","",""],
  ["系统模型","区域电热调度、PyPSA、When2Heat","",""],
  ["主算法","IQL、CQL、TD3+BC","",""],
  ["安全机制","物理安全RL、COptiDICE、CPO","",""],
  ["实验协议","D4RL、CityLearn、MPC比较","",""],
  ["研究边界","相邻工作中的未覆盖问题","",""],
];
overview.getRange("A10:H16").format.wrapText = true;
overview.getRange("A10:H16").format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
overview.getRange("A:A").format.columnWidth = 22;
overview.getRange("B:B").format.columnWidth = 60;
overview.getRange("C:C").format.columnWidth = 30;
overview.getRange("D:D").format.columnWidth = 4;
overview.getRange("E:E").format.columnWidth = 22;
overview.getRange("F:H").format.columnWidth = 24;

matrix.getRange("A1:P1").merge();
matrix.getRange("A1").values = [["核心文献矩阵（摘要级初筛；引用前必须阅读全文核验）"]];
matrix.getRange("A1:P1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 15 },
  verticalAlignment: "center",
};
matrix.getRange("A2:P2").merge();
matrix.getRange("A2").values = [["筛选逻辑：直接相邻能源论文 → 优化强基线 → 数据与环境 → 离线RL与安全RL算法基础。"]];
matrix.getRange("A2:P2").format = { fill: "#EAF2F8", font: { italic: true, color: "#404040" } };
matrix.getRange("A4:P4").values = [[
  "ID","类别","优先级","年份","题名","作者","期刊/会议","DOI或URL",
  "研究对象","核心方法","不确定性/漂移","安全/约束机制","数据/环境",
  "对本研究的价值","主要缺口","阅读状态"
]];
matrix.getRange("A5:P26").values = papers;
const paperTable = matrix.tables.add("A4:P26", true, "LiteratureMatrix");
paperTable.style = "TableStyleMedium2";
matrix.freezePanes.freezeRows(4);
matrix.freezePanes.freezeColumns(4);
matrix.getRange("A4:P26").format.wrapText = true;
matrix.getRange("A4:P4").format = { fill: "#2F75B5", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
matrix.getRange("A5:D26").format.verticalAlignment = "top";
matrix.getRange("E5:P26").format.verticalAlignment = "top";
matrix.getRange("A:A").format.columnWidth = 6;
matrix.getRange("B:B").format.columnWidth = 23;
matrix.getRange("C:C").format.columnWidth = 10;
matrix.getRange("D:D").format.columnWidth = 9;
matrix.getRange("E:E").format.columnWidth = 48;
matrix.getRange("F:F").format.columnWidth = 36;
matrix.getRange("G:G").format.columnWidth = 22;
matrix.getRange("H:H").format.columnWidth = 38;
matrix.getRange("I:P").format.columnWidth = 28;
matrix.getRange("C5:C100").dataValidation = { rule: { type: "list", values: ["核心","高","中","低"] } };
matrix.getRange("P5:P100").dataValidation = { rule: { type: "list", values: ["待读全文","精读中","已精读","可引用","暂不使用","摘要已核验"] } };
matrix.getRange("C5:C26").conditionalFormats.add("containsText", { text: "核心", format: { fill: "#F4CCCC", font: { bold: true, color: "#9C0006" } } });
matrix.getRange("C5:C26").conditionalFormats.add("containsText", { text: "高", format: { fill: "#FFF2CC", font: { color: "#7F6000" } } });

tools.getRange("A1:F1").merge();
tools.getRange("A1").values = [["数据源与开源工具"]];
tools.getRange("A1:F1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 15 } };
tools.getRange("A3:F3").values = [["名称","类型","用于本研究","版本/状态","官方链接","注意事项"]];
tools.getRange("A4:F12").values = resources;
const resourceTable = tools.tables.add("A3:F12", true, "Resources");
resourceTable.style = "TableStyleMedium2";
tools.freezePanes.freezeRows(3);
tools.getRange("A3:F12").format.wrapText = true;
tools.getRange("A:A").format.columnWidth = 24;
tools.getRange("B:B").format.columnWidth = 22;
tools.getRange("C:C").format.columnWidth = 34;
tools.getRange("D:D").format.columnWidth = 16;
tools.getRange("E:E").format.columnWidth = 55;
tools.getRange("F:F").format.columnWidth = 42;

const overviewCheck = await workbook.inspect({
  kind: "table",
  range: "使用说明!A1:H16",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 10,
});
console.log(overviewCheck.ndjson);

const matrixCheck = await workbook.inspect({
  kind: "table",
  range: "核心文献矩阵!A1:P8",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 16,
});
console.log(matrixCheck.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of ["使用说明", "核心文献矩阵", "数据与工具"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(`${outputDir}/${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(`${outputDir}/区域综合能源系统安全离线强化学习_文献矩阵.xlsx`);
