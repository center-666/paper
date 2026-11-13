# Gao 2026公式级排重：全文前置条件尚未满足

基准提交：ffc7c10403c600813beb467f88237f6cd47b9e2e。2026-11-13。

文献：Rui Gao, Guang-Hong Yang, Tianyou Chai, Quality evaluation-based resilient distributed state estimation over time-varying networks via multi-hop communication, Automatica 186 (2026), 112837，DOI [10.1016/j.automatica.2026.112837](https://doi.org/10.1016/j.automatica.2026.112837)。卷、文章号和作者由[Crossref精确记录](sources/gao2026_verified_metadata.json)核实。

**状态：METADATA_ONLY / UNVERIFIED。未取得该文全文，不能给公式号、定理号或覆盖A的结论。** 本文是获取与审计前置状态，不冒充已完成全文排重。

## 1. 可访问范围与具体缺失

本轮核对了本机 C:/Users/zhongxin/Zotero/zotero.sqlite 的精确DOI/题名、C:/Users/zhongxin/Zotero/storage，以及项目 literature_review、第二篇小论文归档目录及ZIP。当前Zotero为51份PDF；精确DOI/题名没有对应条目。项目内候选PDF题名页和归档文件名亦未找到。搜索是本机可见范围，不能据此否定用户在别处已有PDF。

OpenAlex/ Semantic Scholar没有列出可用公开全文；出版社匿名访问不能取得正文；作者公开主页未找到本文副本。一个返回200的元数据响应也不算全文。未尝试绕过机构访问限制。

建议提供路径：C:/Users/zhongxin/shixidoc/mypaper/reviews/g5_direct_competitor_audit/sources/gao2026.pdf。目前该文件不存在。请用已登录的Edge从上面DOI入口下载，或把已有正式PDF放入Zotero并告知实际路径。

## 2. 七项原文核查状态

|要求|当前状态|必须从原式确认的内容|
|---|---|---|
|质量变量|UNVERIFIED|定义、递推、初始化、更新依赖的实际可见信息，不能从题名猜成残差/协方差/信任分数。|
|模态或方向评价|UNVERIFIED|标量、向量、模态级或子空间级质量指标；评价方向是否与被融合方向相同。|
|可疑数据处理|UNVERIFIED|整包丢弃、分量选择、排序剔除、路径选择或矩阵权重，是否会损失必要可观信息。|
|噪声与冗余假设|UNVERIFIED|过程/量测噪声、攻击数量、诚实多数、图鲁棒性、多跳缓存及消息字段。|
|Yang直接适配|UNVERIFIED|具体更新公式、增益设计与攻击入口逐项映射，不以架构名称判断可否继承。|
|缓存MSE风险保证|UNVERIFIED|原定理量词与性能对象；确定性收敛、渐近无偏和有限窗MSE不劣不能互换。|
|G3增量|UNVERIFIED|哪些步骤只是标准观测分解/矩阵加权，哪些需要实际新增证据或算法。|

## 3. A的三个直接竞争者及现有可核定位

1. Gao 2026：最直接，但原式不可得；不填写猜测公式。
2. del Nozal等2022，DOI 10.1109/LCSYS.2021.3082309：已读全文PDF第4页Definition 5、式(9)及Table I，定义更严格re-trust区域；第5页Theorem 1、式(13)对trust切换族给LMI稳定性条件；多跳可观子空间分解已是其方法组成。其保证需相应observer设计，不可直接赋给Yang名义增益。
3. Zhang & Yang 2026，DOI 10.1016/j.jfranklin.2026.108914：PDF第3页式(3)–(7)交换正则化残差；第5页Theorem 1及第6页Theorem 2分别涉及增益和正常均方有界；第7–8页Theorems 3–4的攻击统计结论有特定权限/独立性条件。它增加残差字段，非本项目免费信息。

后两项具体原文读本及定位沿用[G4全文对照](../g4_topic_screen/01_competitor_matrix.md)，旧记录不改。它们不能替代Gao的直接审查。

## 4. 当前决定与终止规则

A暂不进入开发；原因是Gao核心全文阻断，加上当前G3未证实预设信息损失权衡，而不是已证明该问题无意义。

取得全文后若其质量递推和分量/方向接纳经标准变量替换即可实现A的主要操作，则终止该A机制。若不直接覆盖，必须精确列出缺失的不可省略步骤；“它无噪声/多跳、我们随机/缓存”本身不是创新。当前既不能宣称A新颖，也不能宣称Gao已解决它。
