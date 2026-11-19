# P6.1-4：直接竞争矩阵与剩余全文缺口

日期：2026-11-18。FACT＝已核来源；DERIVED＝比较结论；OPEN＝未得足够正文证据。范围固定为附件点名来源及现稿的指定基础近邻，不扩展整个攻击领域。

## 1. 本轮已有全文证据

| 来源及已核题录 | 本轮阅读范围 | 与当前候选的关系 |
|---|---|---|
| Shang–Chen，Automatica 128 (2021) 109555，[DOI](https://doi.org/10.1016/j.automatica.2021.109555) | FULLTEXT；p3–6，Lemma1、Theorem1–3；附录A/B p12–15 | 历史组合、真实损伤与参数优化已有；单时刻高斯约束不直接给联合记录 TV。详见03 |
| Shang–Yu–Chen，TAC 67(4) (2022) 2052–2059，[DOI](https://doi.org/10.1109/TAC.2021.3071948) | FULLTEXT；全部正文；定义1、Theorem1–3、Corollary3 | CGC 精确覆盖健康归一化 f_h；反向攻击与保分布正损伤已有；实际反馈下一事件证书未直接推出。详见01 |
| Haibin Guo 等，TCYB 53(10) (2023) 6714–6724，[DOI](https://doi.org/10.1109/TCYB.2023.3255583) | FULLTEXT；p6715–6720，(9)–(23)、Theorem1–3及证明 | 事件是攻击开关；攻击率+隐蔽限制已有，不等于逐路径载荷峰值。详见03 |
| Ziyi Guo–Zhou–Chen，Automatica 179 (2025) 112463，[DOI](https://doi.org/10.1016/j.automatica.2025.112463) | FULLTEXT；全部正文；Theorem1/2、(14)、(27)–(32) | 比较全部同信息/固定调度/条件矩可行策略，包括非线性；不能贬为只研究线性。详见02 |
| Liu 等，Automatica 136 (2022) 110079，[DOI](https://doi.org/10.1016/j.automatica.2021.110079) | FULLTEXT；p2–6 的假设2.1、定义2.1–2.3、定理3.1/4.1及相关证明 | 真实误差极限、同分布正损伤已有；稳定系统与长期平均、线性攻击及 KL 率不等于本稿对象。详见03 |
| Khazraei–Pfister–Pajic，L4DC/PMLR168 (2022)，[会议入口](https://proceedings.mlr.press/v168/khazraei22a.html) | FULLTEXT；正式13页版本，重点PDF5–6 定义6、定理7、(8)–(10) | 观测前缀分布与任意检测器的 TV 意义已有；不提供此随机事件滤波的损伤界。详见03 |

**FACT。** 前两篇最高优先级在保留目录找到；Shang2021/Guo2023 在用户本轮补充 Zotero 后核验。先前获取日志中的失败记录保留，不能误读成当前仍缺这两篇。六份 PDF 的版本、路径、页码、SHA256 在 06 JSON 中。

**DERIVED。** 此表不能简化成“前人做协方差，本文做真实MSE”或“前人仅线性，本文任意因果”。前者多数确实评价真实误差二阶矩，后者至少 Guo2025 不成立。真正待检的是同一协议/信息/记录/约束/时间目标下的定理蕴含。

## 2. 题录已核、正文仍未关闭的七项

以下 DOI、作者、刊物和时间来自本轮 Crossref/出版社注册题录；这些元数据不提供定理页码。未读全文的一律不判 NOT COVERED。

| 来源 | 本轮证据 | 原文入口及需要关闭的问题 |
|---|---|---|
| Shang–Yu–Chen，Worst-Case Stealthy Innovation-Based Linear Attacks on Remote State Estimation Under Kullback–Leibler Divergence，TAC 67(11),6082–6089 (2022) | METADATA，覆盖 OPEN | [10.1109/TAC.2021.3125430](https://doi.org/10.1109/TAC.2021.3125430)。与3071948为两篇不同论文；需核 KL 约束的时间范围与攻击类 |
| Song–Ye，Optimal Stealthy Attack Against Stochastic Event-Based Scheduling…，IJRNC 32(6),3511–3526 (2022) | ABSTRACT，覆盖 OPEN | [10.1002/rnc.5967](https://doi.org/10.1002/rnc.5967)。摘要确认反馈干扰/伪确认，但不足以核全部权限及最优性定理。在线为2021-12-27，卷期为2022年4月 |
| Xu 等，Integrity Attacks on Remote Estimation With Spatial–Temporal Information Sources，Automatica155,111172 (2023) | METADATA，覆盖 OPEN | [10.1016/j.automatica.2023.111172](https://doi.org/10.1016/j.automatica.2023.111172)。需核安全与可疑数据、联合隐蔽条件和理论范围 |
| Li-Wei Mao–Guang-Hong Yang，Side Information Incorporated ε-Stealthy Attack…，TCYB55,3537–3542 (2025) | METADATA，覆盖 OPEN | [10.1109/TCYB.2025.3565794](https://doi.org/10.1109/TCYB.2025.3565794)。不能把附件关于已上传全文的说法直接当成本轮已核证据 |
| Wei–Zhou–Chen，Integrity Attacks…Varying Data Access: From Visibility to Full Restriction，Automatica174,112162 (2025) | METADATA，覆盖 OPEN | [10.1016/j.automatica.2025.112162](https://doi.org/10.1016/j.automatica.2025.112162)。需核数据可见/可改权限与序列约束 |
| Shuainan Li–Jiacheng Cai，Event-Triggered Optimal Stealthy False Data Injection Attacks With Side Information…，IJSS 在线版 (2026) | METADATA，覆盖 OPEN | [10.1080/00207721.2026.2710888](https://doi.org/10.1080/00207721.2026.2710888)。注册在线日期确为2026-08-19；尚未核全文，不从题名/摘要宣称定理不同 |
| Wei–Zhou–Chen，Integrity Attacks on Remote Estimation Under Sequential Detection，TAC71,536–543 (2026) | METADATA，覆盖 OPEN | [10.1109/TAC.2025.3598115](https://doi.org/10.1109/TAC.2025.3598115)。DOI含2025，卷期为2026年1月；需核序贯观测信息和最坏损伤保证 |

**FACT。** IEEE 入口本轮出现无正文的202响应；Wiley/Taylor & Francis入口出现403；Elsevier API 的若干200响应仅约1.8KB元数据，没有 section/formula。不能因为返回200或名为 full-text-retrieval-response 就记 FULLTEXT。本地盘点范围为 Zotero、指定下载目录及保留 references 目录，不声称全盘绝无改名文件。

**OPEN。** 这七项是有界清单，不是继续发散查新。已请求用户补充的两项已经纳入全文审查；余下缺口在这里给出准确入口，取得后只需核对应的假设、信息集、约束、目标及定理。没有全文就保持 OPEN，不用标题相似度裁决。

## 3. 与已有引用及旧审查的关系

**FACT。** 当前正文已引用 Shang2022、Guo2025、Song2022、Khazraei2022 和 Shang 等 JAS2026 单维加密论文。既有 [novelty_audit.md](../novelty_audit.md) 及 [全文索引](../artifacts/fulltext_source_index.json) 有其他来源的读取记录。本轮继承这些资产，但不把旧部分观测审查的“相对旧稿无新增”误说成当前主稿自身已被外部文献完全覆盖。

**DERIVED。** 有条件保留当前理论候选与宣称文献封口是两件事。已审六篇不足以给全球首创证明；七个缺口也不要求在未解决问题前盲目增加实验。当前可完成的是主审四篇的明确公式映射与反向检验。
