# 两篇新增直接竞争论文：来源核查及全文缺口

日期：2026-11-14。状态：**METADATA VERIFIED / FULL TEXT UNAVAILABLE / METHOD-LEVEL COMPARISON OPEN**。

本轮只核查负责人指定的两篇论文，没有扩大文献数量。本报告不把标题、用户提供的摘要性介绍、索引关键词或Crossref引用关系当作全文证据。未下载任何PDF。

## 1. 精确元数据

|简称|经Crossref及Elsevier接口双重核对的正式题名、作者、出版信息|合法下载入口|
|---|---|---|
|QUICKDET / QUICKGRAD（算法名称待原文核查）|Akanshu Gupta, Saqib Abbas Baba, Abhinava Sikdar, Arpan Chattopadhyay. **Quickest Bayesian and non-Bayesian detection of false data injection attack in remote state estimation**. *Signal Processing* **244** (2026), 110516；卷期日期July 2026。|[DOI 10.1016/j.sigpro.2026.110516](https://doi.org/10.1016/j.sigpro.2026.110516)；[出版社PII](https://www.sciencedirect.com/science/article/pii/S0165168426000307)|
|PALM-DKF（算法名称待原文核查）|Xuemei Mao, Jiacheng He, Gang Wang, Mingzhu Wei, Bei Peng. **Probabilistic attack-aware learning and multi-model inference for distributed state estimation under hybrid DoS and FDI attacks**. *Control Engineering Practice* **175** (2026), 107102；卷期日期October 2026。|[DOI 10.1016/j.conengprac.2026.107102](https://doi.org/10.1016/j.conengprac.2026.107102)；[出版社PII](https://www.sciencedirect.com/science/article/pii/S096706612600345X)|

作者姓名按Crossref记录，不把不同来源的连字符差异解释为不同作者。卷期日期不等于首次在线日期。Crossref和Elsevier响应均未含论文正文或摘要。

## 2. 本地与合法在线访问结果

- `C:/Users/zhongxin/Zotero/storage/`文件名，以及其中`.zotero-ft-cache`、TXT和HTML内精确题名/DOI/article number/算法名搜索：均无命中。
- 项目`reviews/`、`literature_review/`的MD/JSON/TXT全文检索：无命中。
- 常规SQLite只读连接报告`database is locked`；没有关闭Zotero、修改数据库或尝试解锁。另用`mode=ro&immutable=1`核查主库与`.bak`的题名和DOI，无命中。**immutable/备份不包含尚在WAL中的最新条目，故这一检查不证明用户从未下载过。**
- ScienceDirect两篇网页均HTTP 403。未绕过访问控制，也没有利用浏览器凭据。
- Elsevier `content/article/pii/...`两篇均HTTP 200，但响应只有`coredata`出版元数据，**不含`originalText`，不是全文**。两个XML原始响应已保存。
- OpenAlex两篇均标注closed、无repository fulltext、无PDF位置。Semantic Scholar的PALM条目无PDF/摘要，QUICKDET的DOI端点404。
- arXiv题名API请求429，未取得检索结果；一次作者站路径探测404，未取得作者稿。这些访问失败不证明作者稿不存在。

可复查原始记录：`newcomp_quickdet.json`、`newcomp_palmdkf.json`为Crossref完整响应；`newcomp_quickdet_elsevier.xml`、`newcomp_palmdkf_elsevier.xml`为出版方接口完整响应；访问日志见`newcomp_access_log.json`。

## 3. 哪些方法结论目前不能作出

|待核查问题|QUICKDET / QUICKGRAD|PALM-DKF|
|---|---|---|
|攻击具体进入哪个通信字段、是否使用邻居状态包|OPEN：题名不能回答|OPEN：题名不能回答|
|是否需要可信传感器、两跳信息、额外通信或内部模型|OPEN|OPEN|
|是否利用已退出缓存事件的后续本地创新|OPEN|OPEN|
|是否保留多个历史事件及其当前污染集合|OPEN|OPEN|
|是否对归责错误实施拒绝/收缩补偿|OPEN|OPEN|
|误报警、估计MSE与补偿损失约束的精确保证对象|OPEN|OPEN|
|算法递推式、定理号、式号及页码|尚无全文，不填造编号|尚无全文，不填造编号|
|是否能直接替代拟议影响集合机制|UNVERIFIED，不能宣布不能替代|UNVERIFIED，不能宣布不能替代|

用户附件称前者处理相关创新与未知攻击时刻、后者学习链路不确定性并进行多模型融合；这些在本轮仅记录为**USER-SUPPLIED / UNVERIFIED**，不是本轮独立精读结论。尤其PALM的多模型后验可能已足以实现风险敏感或选择性修正，必须核查它的决策量及MSE定理后才能判断差别。

## 4. 全文到齐后的限定阅读任务

QUICKDET只需提取：观测似然及相关性模型、未知攻击时刻处理、假警准则、是否含任何攻击影响估计或恢复动作，以及主定理完整假设。

PALM只需提取：链路模式变量和后验递推、攻击幅值/噪声的先验及可学习性、实际融合/补偿步骤、均方有界或风险定理，以及是否已经输出多个解释下的当前状态分布/集合。

最后与方案A同权限模型逐项比较。不能因它们题名不含Replay/cache而判定未覆盖；也不能仅因都使用概率或集合就判定完全等价。

## 5. 对负责人最小请求及当前门槛

请提供上表两个DOI的正式PDF或合法作者全文，放入Zotero即可；若已经存在，告知实际附件条目名或路径即可，不必重复下载。

**第一关的这两项排重未通过，不等于方案A已被否定；它意味着“现有方法不能直接替代”的论据尚缺。** 数学条件审计可以独立继续，但在两篇原文的关键公式与保证对象核查前，不应宣布创新成立，也不应启动E2/E3性能实验。
