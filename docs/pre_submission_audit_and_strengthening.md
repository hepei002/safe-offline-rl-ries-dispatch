# 投稿前审计与补强报告

对象：`manuscript/latex/main.tex`  
目标期刊：Applied Energy / Elsevier `elsarticle` 格式  
审计日期：2026-06-30

## 1. 审计结论

当前 LaTeX 稿件已经具备“预投稿内审稿”的基本形态：摘要、Highlights、正文结构、图表、参考文献、数据可用性和生成式AI声明均已成型，并且能够稳定编译成PDF。经过本轮补强后，编译日志中不再出现未定义引用、未定义交叉引用、BibTeX字段警告或 Overfull hbox 警告。

但从 Applied Energy 的实际投稿强度看，稿件仍建议在正式提交前完成三项增强：

1. 用正式文献矩阵补强 Related work，尤其是 Applied Energy 近三年相关论文；
2. 对8张图进行投稿级视觉统一，尤其是字体、坐标轴、颜色和图注；
3. 增加一段更清晰的“相对现有 physics-informed safe RL / MPC / offline RL 的区别”，防止创新性被审稿人判定为工程组合。

## 2. 已完成的格式与技术补强

| 项目 | 补强前问题 | 本轮处理 | 当前状态 |
|---|---|---|---|
| LaTeX排版 | 宽表和内部图表计划表导致多处 Overfull hbox | 主文移除内部图表计划表；主表改为可编辑 resizebox 表格；加入 `microtype` | 已修复 |
| Nomenclature | 术语表轻微超宽 | 缩放为 `0.95\textwidth` | 已修复 |
| BibTeX | `empty pages` / `empty journal` 等警告 | 将数据包、书籍、arXiv条目改为更合适的BibTeX类型 | 已修复 |
| 编译目录 | 原PDF可能被占用 | 使用 `build_audit` 目录重新编译 | 已完成 |
| 主文内部附件 | `Figure and table plan` 不适合出现在投稿主稿 | 从 `main.tex` 移除，保留在独立计划文档 | 已完成 |

最终验证：

```text
pdflatex + bibtex + pdflatex + pdflatex
Output written on build_audit/main.pdf
No undefined citations/references
No Overfull hbox warnings
No BibTeX warnings
```

输出文件：

- `manuscript/latex/build_audit/main.pdf`
- `manuscript/latex/build_audit/main.log`
- `manuscript/latex/build_audit/main.bbl`

## 3. 投稿格式审计

| Applied Energy/Elsevier项目 | 当前状态 | 判断 |
|---|---|---|
| `elsarticle`模板 | 使用 `\documentclass[preprint,12pt,authoryear]{elsarticle}` | 通过 |
| 摘要 | 234词 | 通过，低于250词 |
| Highlights | 5条，最长76字符 | 通过，低于85字符 |
| Keywords | 7个关键词 | 可接受，投稿系统中可按要求删减 |
| 图件 | 主文8张图，均可找到PDF源文件 | 通过，但视觉统一仍需增强 |
| 表格 | 4个主文表格，均为可编辑LaTeX文本 | 通过 |
| 参考文献 | 可编译，无BibTeX警告 | 技术通过，学术覆盖仍需增强 |
| 数据可用性 | 已有声明 | 需最终核对数据许可 |
| AI声明 | 已有Elsevier风格声明 | 需投稿前按系统要求核对措辞 |

## 4. 模拟审稿意见

### Reviewer 1：技术可靠性视角

**Overall assessment:**  
稿件提出了一个有实际价值的混合控制框架，将离线RL、OOD风险估计和物理可行性修正结合起来，用于电–热综合能源系统调度。实验链条较完整，包含优化、MPC、规则控制、普通离线RL、固定安全层和自适应安全层对比。

**Major strengths:**

- 问题定义清楚，聚焦分布漂移下的安全失效，而不是只看平均成本；
- 有明确物理模型、离线数据生成流程和多类漂移协议；
- 五种子主实验、成对检验和尾部风险统计提高了可信度；
- 明确承认单种子压力测试只是边界证据。

**Major concerns:**

- 当前安全层承担了很大一部分可行性修正，审稿人可能质疑“RL贡献是否被投影层替代”；
- 计算时间中 adaptive safety 明显高于 raw RL，也未在同等优化器设置下证明快于MPC；
- OOD风险估计的 AUPRC 较低，需强调它不是安全分类器，而只是干预强度信号。

**Required strengthening:**

1. 在 Discussion 中更明确区分“policy learning contribution”和“safety projection contribution”；
2. 增加一个小表或段落说明 adaptive safety 相对 fixed safety 的真正收益是降低修正距离/过度保守，而非单纯安全性；
3. 避免任何“guarantee safety”式表述，保持“under predefined shifts and modeled constraints”。

### Reviewer 2：创新性与文献定位视角

**Overall assessment:**  
稿件的技术组件本身并非全新：offline RL、OOD risk、MPC、安全投影均已有相关研究。潜在创新在于将这些组件组织为面向区域电–热系统分布漂移的可复现实验协议和控制框架。

**Major strengths:**

- 选题贴合 Applied Energy 对低碳、灵活性和智能调度的兴趣；
- 使用公开数据构建可复现案例，而不是纯随机仿真；
- “OOD风险参与控制决策，而非仅事后报警”是较好的贡献点。

**Major concerns:**

- Related work 目前偏薄，缺少 Applied Energy / Energy / IEEE TSG 等近年文献的系统对比；
- 贡献表述需要从“提出一个框架”升级为“解决了哪个现有方法没有解决的缺口”；
- 如果不补足文献，容易被认为是 CQL/IQL + projection 的工程组合。

**Required strengthening:**

1. 增加一张“Positioning table”：MPC、安全RL、offline RL、physics-informed safe RL、本研究；
2. 在 Introduction 最后一段将贡献写得更尖锐：distribution-shift protocol、OOD-to-action coupling、cost-safety-conservatism evidence；
3. 补充近3年 Applied Energy 中 RL/安全RL/多能源调度相关引用。

### Reviewer 3：可读性与能源系统读者视角

**Overall assessment:**  
稿件结构已经清楚，但方法部分对非RL读者仍略技术化。Applied Energy 读者可能更关心能源系统意义：为什么这种安全层对实际园区调度有价值、什么情况下比MPC更值得用、部署边界在哪里。

**Major strengths:**

- 系统规模、设备参数和数据来源清楚；
- 图件覆盖从数据、方法、主结果到压力测试的完整链条；
- Limitations 写得相对诚实，有助于降低过度声称风险。

**Major concerns:**

- Fig. 1 需要让能源系统读者一眼看懂“风险分数如何改变动作”；
- Results 中数字较多，建议每节开头用一句“结论句”压住细节；
- 数据集是缩放公开数据，不是真实园区实测，应持续避免“real industrial park”措辞。

**Required strengthening:**

1. 对每张图增加一句“Take-home message”式图注开头；
2. 在 Case study 中再次强调“simulated benchmark calibrated from public time series”；
3. 在 Practical implications 中说明该方法适合先作为 advisory/safety filter，而非直接闭环控制器。

## 5. Cross-review synthesis

三位审稿视角的共同判断是：稿件现在已经不是“不能投”的状态，而是进入了“可以内审/预投稿打磨”的状态。最强证据是完整实验链条和安全风险显著降低；最大风险是创新性叙事和文献定位仍不够锋利。

最需要优先解决的三件事：

1. **文献定位补强**：尤其是与 Applied Energy 近年安全RL、多能源调度、MPC+学习方法的区别；
2. **方法贡献边界补强**：说明安全收益来自 OOD-aware projection，而不是事后用优化器完全覆盖RL；
3. **图件投稿级统一**：当前图能支撑论文，但还不像最终投稿图，需要统一字体、颜色、线宽、图注和面板逻辑。

## 6. 剩余高优先级任务

| 优先级 | 任务 | 目的 |
|---|---|---|
| P0 | 补文献矩阵并更新 `references.bib` | 降低创新性被质疑风险 |
| P0 | 加一张方法定位表 | 让审稿人快速看到与现有方法的差异 |
| P1 | 重绘/统一8张主图 | 提升AE投稿观感 |
| P1 | 检查所有图注是否有清晰结论句 | 改善能源读者可读性 |
| P1 | 细化Data availability和许可措辞 | 避免数据合规问题 |
| P2 | 准备cover letter和highlights系统版本 | 进入正式投稿流程 |

