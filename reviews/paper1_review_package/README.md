# 第一篇论文统一审阅入口

汇集日期：2026-11-19。当前为投稿前研究候选，未通过最终论文准入；本次不修改正文、不重新编译或运行旧实验。

## 先读这四项

1. [双栏阅读稿PDF](../../papers/latex_ecust_20261102/paper.pdf)；[投稿版PDF](../../papers/latex_ecust_20261102/paper_submission.pdf)。这是原有2026-11-03稿件快照，不是本轮修订版。
2. [补充证明PDF](../../papers/latex_ecust_20261102/supplement.pdf)。
3. [问题解释和模拟审稿意见](reviewer_assessment.md)：说明论文究竟回答什么、有什么增量候选、为什么目前不建议直接投稿。
4. [最新P6.1定理级文献综合判断](../paper1_p61_theorem_literature_audit/05_theorem_level_synthesis_and_decision.md)。该目录从 `75b3e5b73d3871817dc8a55b474d9c445638ff84` 原样汇入；后发现的历史Song全文笔记见下文，旧状态不覆盖。

## 数学、代码和已有结果

- [完整稿件源码与构建说明](../../papers/latex_ecust_20261102/README.md)。主入口 `paper.tex` 实际引用 `ecust_typeset/theory.tex`、`ecust_typeset/numerical.tex`，不要只改源模板却误以为编译正文已改变。
- [主定理与完整联合日志构造](../../papers/latex_ecust_20261102/ecust_typeset/theory.tex)、[联合核](../../papers/latex_ecust_20261102/ecust_typeset/main_joint_kernel.tex)、[记录删减](../../papers/latex_ecust_20261102/record_design.tex)。
- [作者原有数值代码及结果目录](../../papers/latex_ecust_20261102/vector_data/)、[计算入口](../../papers/latex_ecust_20261102/experiments.py)、[物理过程核验代码](../../papers/latex_ecust_20261102/physical_check.py)、[记录删减结果](../../papers/latex_ecust_20261102/record_study/)。只汇集既有文件，未产生新结果。
- [联合TV独立审查](../../papers/latex_ecust_20261102/final_review/joint_tv_audit.md)、[日志重建映射审查](../../papers/latex_ecust_20261102/final_review/record_mapping_audit.md)。
- [部分观测上界审计及反例](../theorem_audit.md)、[对应增量审查](../novelty_audit.md)、[方向判决](../paper_decision.md)。这些是受限扩展材料，不是当前主稿已获全部验收；不将部分观测扩展重复包装为新论文。
- [新增汇集的本地复核记录](historical_local_supplement/)，含 `review_checks`、`clarity_review`、`submission_review`、`fulltext_review`、历史版本溯源与检查脚本。

## 文献与发表定位

- [P6.1模型](../paper1_p61_theorem_literature_audit/00_scope_and_model.md)、[Shang2022](../paper1_p61_theorem_literature_audit/01_shang2022_CGC_and_record_comparison.md)、[Guo2025](../paper1_p61_theorem_literature_audit/02_guo2025_policy_class_and_optimality.md)、[历史攻击等近邻](../paper1_p61_theorem_literature_audit/03_history_attack_triggered_neighbors_and_foundations.md)。
- [P6.1原文来源状态](../paper1_p61_theorem_literature_audit/04_competitor_matrix_and_download_gaps.md)、[来源哈希](../paper1_p61_theorem_literature_audit/06_sources_and_integrity.json)。
- [学报已发表论文的具体切口比较](../research_portfolio_journal_20261119/02_journal_article_comparison.md)、[有限验收卡](../research_portfolio_journal_20261119/03_one_problem_acceptance_card.md)。

### 新发现的历史状态冲突

本次从原稿本地发布目录找到 [2026-10-20 Song–Ye全文精读笔记](historical_local_supplement/fulltext_review/song_review.md) 和 [原来源登记](historical_local_supplement/fulltext_review/source_manifest.json)，记录正式版16页、公式定位及SHA256。它说明“从未取得/从未读过Song全文”不准确；P6.1的后续获取失败不抹去该历史证据。

但在本次核对的旧研究PDF、Zotero和literature_review目录内，未找到与登记大小906597字节及SHA256匹配的原PDF；原记录指向另一台电脑的 `C:/Users/26626` 和 `E:` 路径。故当前应区分：**已有历史全文审读记录；本机原PDF重新核验仍OPEN**。不是本轮又完整精读了Song原文，也不能只靠旧笔记关闭当前同版本的最后审查。

## 版本和完整性

`historical_local_supplement` 的材料从本地原始发布快照复制，原文保留历史路径、日期、旧稿名称及当时观点；它们是历史证据，不自动替代P6.1最新裁决。部分脚本依赖旧目录，不承诺此目录独立执行全部审计。稿件既有可移植构建入口见上方说明。

[asset_manifest.json](asset_manifest.json) 记录每个新增文件的原路径/固定提交与SHA256；[delivery_validation.json](delivery_validation.json) 核对原样复制、既有稿件字节未变、链接与文件清单。第三方论文PDF及提取全文不公开上传，保留题录、DOI、页码和来源哈希；构建日志、缓存和重复整套旧稿未重复上传。现有第一篇稿件、作者代码、图表、主要保存结果，以及此次补齐的实质审查均可从本入口访问。
