# 可信反馈下远程估计的隐蔽攻击损伤界：结构性大修候选稿

本目录是在基准提交 `696c1f2d` 上建立的独立候选稿。原冻结版 `paper1_submission_20261120/` 与此前未跟踪的 `paper1_submission_candidate_20261119/` 均保留。本稿尚未冻结、未投稿，也未补入作者行政信息。

本轮不改定理、证明、原始结果或结论范围，主要重写研究问题与章节叙事，明确完整日志字段和攻击时序，解释精确反馈下的事件统计机制，并将数值结果压缩为损伤分解、双预算解析界、量化见证和记录分辨率四部分。双预算图复用 `papers/latex_ecust_20261102/` 中已保存的模型与数据；没有重新运行仿真。

- [主文件](paper.tex)、[中文正文与证明](sections/)、[英文摘要](english_abstract.tex)
- [构建脚本](build.py)、[构建记录](build_validation.json)、[文件哈希](release_manifest.json)
- [基准终审报告](../../reviews/paper1_submission_final_audit_20261120/README.md)
- [既有量化实验审查记录](../../reviews/paper1_e1_scalar_execution/02_referee_evidence_audit.md)

使用仓库环境中的 XeLaTeX、ctex 和所需中文字体运行 `python build.py`。构建读取已保存的 E1 审计状态，不运行实验。正文中的量化图读取固定汇总数据；双预算图从既有解析界与十个保存点复用。
