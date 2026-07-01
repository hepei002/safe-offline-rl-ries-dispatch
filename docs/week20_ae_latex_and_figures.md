# 第20周：Applied Energy LaTeX稿件包与图表补充计划

## 1. 本周目标

本周目标是将第17--19周形成的英文完整初稿转化为 Applied Energy/Elsevier 风格的 LaTeX 稿件包，并补齐论文主文预期图和表。稿件使用 Elsevier `elsarticle` 类组织，保留可编辑表格、独立图件路径、参考文献库、Highlights 和投稿准备清单。

## 2. Applied Energy格式约束

根据当前 Elsevier Applied Energy 作者指南，本稿件包采用以下约束：

- LaTeX使用 Elsevier `elsarticle` 模板；
- Abstract 控制在250词以内；
- Highlights为3--5条，每条不超过85个字符；
- 表格使用可编辑文本，不使用截图；
- 图件作为独立文件引用，并保留源数据和可复现生成脚本；
- 生成式AI使用说明、数据可用性说明和引用格式需在投稿前最终核对。

官方作者指南：<https://www.elsevier.com/journals/applied-energy/0306-2619/guide-for-authors>

## 3. 预期主文图

| 图号 | 结论任务 | 图型 | 当前源文件 | 审稿风险 |
|---|---|---|---|---|
| Fig. 1 | 说明离线RL、OOD风险和自适应安全层如何闭环 | schematic-led composite | `results/figures/adaptive_safety/adaptive_safety_method_flow.*` | 需避免流程图像“方法堆砌”，突出风险如何改变动作 |
| Fig. 2 | 证明数据和系统负荷具有季节性与调度压力 | quantitative grid | `results/figures/system_profiles/*` | 需在图注中说明公开数据经缩放而非实测园区 |
| Fig. 3 | 展示确定性模型能形成物理可行调度 | quantitative grid | `results/figures/deterministic_dispatch/*` | 三个典型日可能占版面，投稿版可合并为一张多面板图 |
| Fig. 4 | 给出主基线结果：原始离线RL快但不安全，自适应安全显著降低硬安全成本 | hero comparison | `results/figures/week13_14/week13_main_results.*` | 必须清楚标注hard safety cost单位/定义 |
| Fig. 5 | 支撑机制：消融和敏感性说明安全层不是偶然有效 | robustness grid | `results/figures/week13_14/week14_ablation_sensitivity.*` | 避免过度解释单个敏感性点 |
| Fig. 6 | 支撑泛化：跨年、跨季节、气候和复合压力测试 | robustness grid | `results/figures/week15_16/week15_stress_summary.*` | 单种子压力测试只能作为边界证据 |
| Fig. 7 | 解释自适应安全层何时介入 | time-series mechanism | `results/figures/week15_16/week15_intervention_trajectory.*` | 需说明该图是机制展示而非统计主结果 |
| Fig. 8 | 汇总置信区间、尾部风险和失效模式 | statistical summary | `results/figures/week15_16/week16_statistics_summary.*` | 需要区分五种子统计与单种子压力筛查 |

## 4. 预期主文表

| 表号 | 内容 | 生成文件 |
|---|---|---|
| Table 1 | 园区规模和设备参数 | `manuscript/latex/tables/table_system_parameters.tex` |
| Table 2 | 分布漂移场景定义 | `manuscript/latex/tables/table_shift_protocol.tex` |
| Table 3 | 主要调度结果 | `manuscript/latex/tables/table_main_results.tex` |
| Table 4 | 五种子场景成对显著性检验 | `manuscript/latex/tables/table_paired_tests.tex` |
| Table 5 | 主文图件计划与证据角色 | `manuscript/latex/tables/table_figure_plan.tex` |

## 5. 第20周产物

- `manuscript/latex/main.tex`
- `manuscript/latex/references.bib`
- `manuscript/latex/tables/*.tex`
- `manuscript/latex/README.md`
- `manuscript/latex/figure_table_plan.md`
- `scripts/generate_week20_latex_tables.py`

## 6. 投稿前仍需完成

1. 用最终文献矩阵替换当前BibTeX占位引用；
2. 将图件标题、坐标轴、字体和线宽统一到AE投稿版；
3. 根据最终图版面决定Fig. 2和Fig. 3是否合并或转入补充材料；
4. 核对数据许可和可公开分发范围；
5. 若需要正式PDF，确认本机安装了`elsarticle`和可用LaTeX工具链。

## 7. 编译验证

已使用 TeX Live 2024 和 Elsevier `elsarticle` 类完成编译：

```powershell
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
bibtex build\main
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```

输出PDF：

- `manuscript/latex/build/main.pdf`

编译状态：

- PDF生成成功，共22页；
- 未发现未定义引用或未定义交叉引用；
- BibTeX有少量字段不完整警告，后续需用正式文献矩阵补齐页码、期刊和出版信息；
- 存在若干 `Overfull \hbox` 警告，主要来自宽表格，投稿排版前建议将 Table 3 和 Figure-plan table 改为横向表、缩小字号或转入补充材料。