# 安全状态估计与通信论文工作区

本仓库管理两篇控制与状态估计论文的精选源码、研究记录和可复核计算入口。原始 Zotero 库、第三方论文全文、虚拟环境和完整 Monte Carlo 轨迹留在本地，不随公开仓库分发。

## 当前稿件

| 论文 | 当前版本 | 状态 |
|---|---|---|
| [随机触发估计的隐蔽攻击损伤界](papers/latex_ecust_20261102/README.md) | 2026-11-03 华理学报投稿准备稿快照，含 TeX、图表、数值输入/摘要与审计记录 | 匿名准备稿，作者和基金元数据待据实填写，尚未记录为已投稿 |
| [有限攻击预算下的 ACK 安全发送延后](papers/paper2_ack_budget_deadline/README.md) | 2026-11-09 14 页大修讨论稿快照 | 单次截止理论候选；相近误差下通信优势未通过强基准，投稿价值仍待判断 |

旧文件 `第二篇小论文.zip`（约 839 MB）和原始目录 `第二篇小论文/` 未纳入 Git。两个论文快照来自原目录，保留源文件哈希和版本说明；原始资料没有被移动或覆盖。

## 研究结论

- [当前项目管理和研究状态](docs/PROJECT_MANAGEMENT.md)
- [研究与文献索引](research/README.md)
- [部分观测候选的精读比较和立项判断](research/literature_comparison.md)
- [第二轮核心定理复审：执行摘要与研究决策](reviews/executive_summary.md)
- [FDI / Replay分布式估计：精华报告及网页版GPT审阅材料](reviews/fdi_replay_20261112/research_digest.md)
- [FDI / Replay分布式估计：精华报告及网页版GPT审阅包](reviews/fdi_replay_20261112/research_digest.md)
- [文献证据矩阵](research/references/文献证据矩阵_42篇.md) 与 [BibTeX](research/references/survey_references.bib)
- [实验工程说明](simulation/README.md)

缓存驻留均值的通用 FDI/Replay 主张已经停止。第二轮审计支持部分观测候选在明确条件下的有限时刻上界，但其秩条件不是必要条件；新增主要是旧稿适用范围的推广，目前建议限量并入旧稿，不作为独立论文立项。 ACK 理论稿也保留了相近误差基准未支持资源优势的结果。

## 本地复现

Python 环境与小型代数核验：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r simulation\requirements-lock.txt
.\.venv\Scripts\python.exe simulation\verify.py --config simulation\config.json --output simulation\verification_new.json
```

完整五节点轨迹、论文编译环境及其他数值材料不属于公开仓库的可移植复现包。每个论文快照 README 会说明其本地依赖和复现边界。请先阅读 [项目管理说明](docs/PROJECT_MANAGEMENT.md)。

## 使用边界

当前没有添加开源许可证，因此代码和稿件保留各自原有版权。仓库公开不代表其中引用的第三方内容获得再分发授权；第三方论文 PDF、Zotero 数据和个人凭据不应提交。
