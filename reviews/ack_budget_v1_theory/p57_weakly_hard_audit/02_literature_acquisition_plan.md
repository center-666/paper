# P5.7-0：文献获取计划与下载清单

日期：2026-11-18。仅准备 A–E 来源，不进行全文定理比较。题录及机构页面查询的原始摘录、状态与时间见 [证据清单](03_stage0_evidence_and_integrity.json)。所有公式级覆盖关系仍为 **OPEN**。

## 1. 本地盘点与证据级别

**FACT。** 对本地 Zotero 数据库以 immutable 只读连接查询了五个 DOI 及 weakly / deadline-driven window / Znati 题名词；对 Zotero storage、C:/Users/zhongxin/Downloads、D:/Downloads 做了相关 PDF 文件名检索，未找到这五篇的匹配项。范围仅限题录和文件名，不表示全盘不存在改名 PDF，也不表示全文获取不可能。没有改写 Zotero。

FULLTEXT 必须同时满足取得完整文件并读过相关原文；只下载文件不算完成全文审查。PARTIAL 为部分正文，ABSTRACT 为仅摘要，METADATA 为题录，OPEN 为尚不能核实。下载状态、证据级别和定理覆盖结论分别记录。

## 2. 五篇来源与当前缺口

| 文献 | 题录与入口 | 本轮证据级别 | 获取状态及下一阶段待核内容 |
|---|---|---|---|
| A | Bernat, Burns, Llamosí. *Weakly Hard Real-Time Systems*. IEEE TC 50(4), 308–321, 2001. [DOI](https://doi.org/10.1109/12.919277)；[候选 PDF](https://cs.gmu.edu/~aydin/cs773/papers/whrt4.pdf) | **OPEN（本轮独立核验未完成；题录继承任务书）** | Crossref 返回 HTTP 429；PDF HEAD 因本地证书链验证失败而未确认，不等于链接失效。请提供完整刊版；核对一般窗口约束、语言及状态理论 |
| B | Bernat, Cayssials. *Guaranteed On-Line Weakly-Hard Real-Time Systems*. RTSS 2001, 25–35. [DOI](https://doi.org/10.1109/REAL.2001.990593)；[White Rose 记录](https://eprints.whiterose.ac.uk/id/eprint/5506/) | **ABSTRACT** | 机构元数据独立确认作者、题名、DOI、页码；记录含摘要，但 full_text_status=none。需要完整会议论文，之后核对 BMS 的状态与切换保证 |
| C | Linsenmayer, Hertneck, Allgöwer. *Linear Weakly Hard Real-Time Control Systems: Time- and Event-Triggered Stabilization*. IEEE TAC 66(4), 1932–1939, 2021. [DOI](https://doi.org/10.1109/TAC.2020.3000981) | **METADATA** | Crossref 确认题录。未取得正文；需要刊版或可与刊版逐项对齐的作者接受稿 |
| D | Hertneck, Linsenmayer, Allgöwer. *Efficient Stability Analysis Approaches for Nonlinear Weakly-Hard Real-Time Control Systems*. Automatica 133, 109868, 2021. [DOI](https://doi.org/10.1016/j.automatica.2021.109868) | **METADATA** | Crossref 确认题录。未取得正文；需明确其合法序列模型与分析保证是否能覆盖协议生成约束 |
| E | T. Znati. *A Deadline-Driven Window Protocol for Transmission of Hard Real-Time Traffic*. Tenth Annual International Phoenix Conference on Computers and Communications, 1991, 667–673. [DOI](https://doi.org/10.1109/PCCC.1991.113878) | **METADATA** | **本轮 Crossref 独立确认 DOI、题名、作者、会议名及页码对应。** 尚未取得或核实正文版本，协议和定理关系继续 OPEN |

**FACT。** 本阶段没有保存任何第三方 PDF，因此所有 PDF SHA256、实际文件版本和定理定位均为空并注明“尚未取得”，不是遗漏已取得文件的哈希。JSON 内可见的 Crossref `link` 为出版社元数据返回值，不代表该链接已成功获取全文，不建议以 staging 地址代替正式 DOI 入口。

## 3. 需要用户下载的文件

**OPEN（等待原文）。** 五篇均需要全文。建议先补 B 和 E，再补 A，随后 C、D；这只是获取优先级，不是提前授权任何审查阶段。A 可先尝试上表直接 PDF，B 的机构页面目前只有摘要，B/E 宜通过学校或机构的 IEEE Xplore 权限下载。C、D 使用上表 DOI 定位正式期刊文章。

取得后可放入 Zotero，保留完整题名及 DOI。只有摘要页、引用页或首页截图不足以进行公式级排重。本轮不将 PDF 加入 Git 仓库。

## 4. 术语事实与未核事实分开

| 术语 | 本阶段所能确认的内容 | 尚不能确认的内容 |
|---|---|---|
| Bi-Modal Scheduler（BMS） | **FACT（摘要级）**：B 的机构记录摘要明确出现该名称 | 正文状态、定义、公式、证明及与 ACK-V1 的关系 |
| panic mode | **FACT（摘要级）**：B 的摘要出现 normal / panic 两模式描述 | 精确进入时机、是否延后进入、可调度性假设 |
| p-fragility | **OPEN** | 是否出现于指定原文、定义及其定理作用 |
| criticality | **OPEN** | 哪篇原文、何种定义，不能用日常含义替代数学定义 |
| delayed panic mode | **OPEN** | 本阶段没有正文证据，不把前轮助手措辞作为文献事实 |

以上术语仅作为以后查原文的检索项。未取得正文时不编造页码、定义编号，也不把摘要承诺当作已核定理。

## 5. 下一阶段的证据表设计（尚未执行）

取得每篇原文后，应先记录 DOI、来源 URL、文件 SHA256、刊版/作者稿、PDF 页码与印刷页码对应，再为每项影响创新性的结论填写：

1. 原文页码及定义/公式/定理编号；原始假设和完整结论。
2. 与 ACK-V1 的状态、动作、转移、初态、时间推进及语言的明确映射。
3. 映射是同构、双模拟、单向模拟、语言包含还是指标形式相似，并提供证明。
4. 是否保持从空历史可达量词、自然锚点、高请求强制等待和有效阻断守卫。
5. 能否直接推出临界 L=B+3 的禁 101、严格差距排除以及 B≥2,L≥B+4 的构造；若需新证明，具体列明新增步骤。
6. 结论标签 FACT / DERIVED / OPEN / HYPOTHESIS；未取全文不能写 NOT COVERED。

**OPEN。** 当前没有任何一篇被判为“覆盖”或“不覆盖”候选分类。一般理论可能通过状态扩充直接给出结果，也可能仍需协议特定的实质结构证明；P5.7-0 不预设方向。后续必须接受最终 NO-GO 的可能，不能因暂未找到同式而给 GO。

本阶段停止，等待负责人审核；不自动开始 A–E。
