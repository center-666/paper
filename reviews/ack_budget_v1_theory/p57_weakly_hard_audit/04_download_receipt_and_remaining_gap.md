# P5.7-0 补录：已下载文献收件核验

日期：2026-11-18。基线：de807527af90f2040e9402fafedc6287dbababa1。范围：接收用户新下载的文献，检查身份、文件可读性、版本和哈希；不开展 A–E 的公式级排重。

## 1. 收件结果

**FACT。** 在 Zotero storage 找到目标文献 B、C、D、E 共四份 PDF。四份均可打开，全部页面可渲染；页数与已核题录或文章首尾页相符。具体题名、DOI、文件路径、版本判据和完整 SHA256 见 [05_received_pdf_manifest.json](05_received_pdf_manifest.json)。原四份阶段准备文件保持原样，本补录更新的是当前文献获取状态，不回写过去的检查记录。

| 编号 | 文献 | PDF 页数 / 印刷页码 | 版本与核验依据 | 获取状态 / 审读状态 |
|---|---|---|---|---|
| A | Bernat–Burns–Llamosí, Weakly Hard Real-Time Systems, 2001 | 尚无本地文件 | DOI 10.1109/12.919277；本次未定位 | **OPEN**：仍需文件或保存路径 |
| B | Bernat–Cayssials, Guaranteed On-Line Weakly-Hard Real-Time Systems, 2001 | 11 页 / 25–35 | 正式会议 PDF；标题、作者、IEEE 标记、PDF 元数据 DOI 和页标签吻合 | **FACT**：PDF 已取得；审读 **PARTIAL**，限身份与首尾页 |
| C | Linsenmayer–Hertneck–Allgöwer, Linear Weakly Hard Real-Time Control Systems: Time- and Event-Triggered Stabilization, 2021 | 8 页 / 1932–1939 | IEEE TAC 66(4) 刊版；首页卷期及首尾印刷页码，元数据 DOI 吻合 | **FACT**：PDF 已取得；审读 **PARTIAL**，限身份与首尾页 |
| D | Hertneck–Linsenmayer–Allgöwer, Efficient Stability Analysis Approaches for Nonlinear Weakly-Hard Real-Time Control Systems, 2021 | 13 页 / 文章内部页码 1–13 | Automatica 133, 109868 刊版；首页题名、作者、文章号、DOI 与末页 13 | **FACT**：PDF 已取得；审读 **PARTIAL**，限身份与首尾页 |
| E | Znati, A Deadline-Driven Window Protocol for Transmission of Hard Real-Time Traffic, 1991 | 7 页 / 667–673 | IEEE 会议扫描版；PDF 元数据 DOI，视觉核对首页题名、作者及 667、末页 673 | **FACT**：PDF 已取得；审读 **PARTIAL**，限身份与首尾页 |

**FACT。** 文件接收成功与 FULLTEXT 理论审读完成不是同一状态。此处 PARTIAL 指只检查部分原文页面以确认身份和边界，并非只有部分 PDF。B–E 已有正文载体，但尚未逐项审读有关定义、定理和证明，不升级为 FULLTEXT（相关原文已审）。四篇与 ACK-V1 的覆盖关系全部保持 **OPEN**。

**FACT。** 页数、可渲染性与首尾核对是文件完整性初检，不等同于逐页数学内容校对。C 的 PDF 内置页标签为 1–8，正文印刷页码为 1932–1939，今后引证应同时标明两种页码。D 使用文章号 109868，不能将其写成起始页码。

## 2. 扫描与文本层限制

**FACT。** B 的文本层含 OCR 痕迹；后续若引用符号、公式及不等号，须回看 PDF 图像。C、D 有可提取的正文文本，仍需核对公式版式。

**FACT。** E 的每页文本提取仅返回下载授权水印，正文为扫描图像。已视觉核对首页和末页，不能由“文本搜索没有命中”推断某个术语或定理不存在。本阶段没有运行全文 OCR；后续获得审查授权后，应逐页看图或进行 OCR 并人工核对公式。

## 3. A 的剩余获取缺口

**FACT。** 本次在 Zotero storage、C:/Users/zhongxin/Downloads、D:/Downloads 检查相关 PDF 文件名，并盘点最近两小时 PDF，找到 B–E，未定位 A。该范围不是全盘内容搜索，不能据此断言用户没有下载 A。

**FACT。** 对 Zotero 实时数据库的只读连接遇到 database is locked；随后 immutable 主文件快照未呈现新导入记录。由于该方式可能不包含尚未检查点化的 WAL 更新，数据库无匹配不作为缺失证据。本轮以已存在的 PDF 实体核验 B–E；未关闭 Zotero、改写数据库或触碰 WAL。

**OPEN。** A 如已另存，请提供文件名或目录，以便补齐。入口保留如下：

- DOI：https://doi.org/10.1109/12.919277
- 用户提供的候选 PDF：https://cs.gmu.edu/~aydin/cs773/papers/whrt4.pdf

候选链接沿用原获取计划，本次没有重新联网测试，不声称已经成功下载。

## 4. 保护与停止边界

**FACT。** 本轮仅新增本收件报告及一份 PDF 清单 JSON。58 个已保护历史文件与原四份 P5.7-0 草稿均通过 SHA256 对照。Git HEAD 仍为指定基线；没有修改旧稿、旧报告、算法、参数或实验数据，没有运行实验、提交或推送。第三方 PDF 留在本地 Zotero，未复制进仓库。

**OPEN。** 本轮不评判禁 101、可达性分类或弱硬实时理论的等价关系。用户告知下载完成用于补齐材料，不视为已经审核通过 P5.7-0 或授权自动开始下一阶段。收件核验完成后停止，等待负责人审核。
