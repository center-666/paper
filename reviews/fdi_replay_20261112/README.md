# FDI / Replay分布式估计：精读与问题筛选

日期：2026-11-12。研究目标：一篇关于分布式滤波网络攻击与安全防御的增量型学报论文。本轮按最新要求回到邻居估计载荷攻击主线；不继续发展随机触发TV损伤定理。

- **先读：[精华报告与推荐问题](research_digest.md)**
- **外部审阅包：[给网页版GPT的独立材料](web_review_packet.md)**，不要求对方读取本地项目。
- [逐篇精读笔记](literature_reading_notes.md)：28篇可用全文的模型、算法、攻击权限、定理/公式与实验；区分直接主线与相邻基础。
- [问题筛选](problem_selection.md)：最多3个问题，比较已证明缺陷、模型推断和未验证假设。
- [既有方案与证据](project_evidence.md)：工程设置、攻击权限、失败结果和筛选审计。
- [G2 Replay闭环最终报告](g2_final_report.md)：同机会攻击损失、缓存退出后的传播、报警时序、自然恢复和研究决定；原始 v3 Run 与失败 Run 均保留。
- [G2 源码换行归一化指纹](g2_source_fingerprints.json)：保留 Run 的工作区字节哈希，并提供 CRLF→LF 后的核验哈希。
- [逐篇阅读位置表](sources/reading_locators.csv)、[全文哈希/来源索引](sources/fulltext_index.json)、[题录元数据](sources/metadata.json)。
- [小型解析诊断](code/mechanism_checks.py)：只核对公式与简化假设，不是新方法性能仿真。
- [给网页版GPT的独立审阅材料](web_review_packet.md)：含攻击权限、关键竞争方法、旧实验负结果与明确审阅问题。
- [交付校验报告](sources/delivery_validation.json)与[方法级文献BibTeX](sources/references.bib)。
- [G1验收文件](identifiability_audit.md)：可辨识性、基线等价性、未执行计划、样本量和唯一结论。
- G1只读代码复核见[GLS/episode审计](code/g1_reaudit.py)与[配对样本量重算](code/g1_sample_size.py)；本轮无新Run ID、无新仿真。
- [G1交付校验](g1_delivery_validation.json)：来源运行哈希、episode删失与旧文件未改检查。

证据标记：L＝文献原文的假设/结论；M＝由文献模型或公式可直接推导；E＝项目已有实验；H＝候选研究假设；U＝全文或结论尚未核实。L不代表本轮重新证明了原文所有结论。

## 下载和保留

**本轮Codex新增成功下载的论文PDF为0篇。** Yu等SPL 2025、Xing等TIFS 2025是用户本轮新加入Zotero的两篇全文；我只读复制并提取，未修改Zotero原件。其余26篇来自已有Zotero/本地全文。本轮保存8项书目来源核查及访问响应，无新增第三方PDF分发；原作者论文PDF和提取全文保留于被Git忽略的literature_review本地目录。

完整状态显示全局doi核对、PDF页码、hash和逐篇阅读locators。不同版本页码不混用；会议版页码使用PDF内出版页码，页序另列。
