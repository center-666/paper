# 第二轮核心定理与增量审查

审查对象：随机触发记录、隐蔽载荷攻击与攻击可达方向损伤界。日期：2026-11-12。

按数学审计、定理级排重、论文决策的顺序工作。正式旧稿、既有数据、第一轮结论文件均不覆盖。

- [数学审计](theorem_audit.md)
- [文献与旧稿排重](novelty_audit.md)
- [论文决策与一页执行摘要](paper_decision.md)
- [独立数值核验入口](code/audit_round2.py)
- [一页中文执行摘要](executive_summary.md)
- [文献来源、页数与哈希](artifacts/fulltext_source_index.json)及[核对后的BibTeX](artifacts/round2_references.bib)
- [全部失败/边界项目](artifacts/failed_and_boundary_cases.json)
- `artifacts/`：新核验结果、原结果哈希清单、文献来源索引。

状态标签：PROVED 完整独立证明；CONDITIONAL 依赖明确的条件；OPEN 尚未证明；DISPROVED 已有反例；UNVERIFIED 证据不足。数值检查通过不升级为数学证明。第三方 PDF 与全文保存在本地 `literature_review/round2_20261112/`，不随公开仓库分发。

最终数值运行是`artifacts/run_20261112_02/`；01版保留。九个案例还分别从独立命令行运行，命令与退出状态见`artifacts/independent_cli/invocations.json`。输入依赖与原结果位于已纳入Git的`simulation/`；本轮新仿真无需Zotero或第三方PDF。全文重新抽取另需`pypdf==7.0.1`；书目元数据抓取使用Windows自带curl，网络访问失败也保存。

`code/validate_delivery.py`核对报告链接、原结果哈希、11篇原始PDF哈希和稿件未改状态；该完整来源核验需要本机保留的原PDF，不属于纯Git克隆后的数值案例依赖。`artifacts/delivery_validation.json`保存本机核验结果。
