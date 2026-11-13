# G4增量型学报研究问题筛选

**本轮决定：不立即立题。** G3按预注册停在Gate A pilot；B的小预算主动恢复未显示足够收益。最多保留A、B的一般问题，当前实例均不继续开发。

交付入口：

- [01 直接竞争方法与全文证据](01_competitor_matrix.md)
- [02 五个问题的具体模型、机制和失败条件](02_candidate_problem_models.md)
- [03 理论框架、完整推导及解析反例](03_theorem_feasibility.md)
- [04 主动恢复的最小价值实验](04_minimal_value_of_recovery.md)
- [05 一页摘要、排序与执行决定](05_research_ranking.md)
- [G3实际执行与停止原因](../g3_partial_observability/execution_report.md)
- [缺失全文及下载入口](sources/download_requests.md)

B仿真只复用8个G2已有seed，精确枚举67个小预算日程，不作确认性统计。原G2全部输入及共享仿真源只读；新发送允许携带sender历史污染。结果区分未来真误差oracle、固定发送、随机发送、正常误触发条件损失和攻击特异恢复。

主要Run：

|Run ID|内容|
|---|---|
|`2026-11-13_g4_recovery_budget_r01`|预先登记的11机会、最多2额外广播、67日程完整结果|
|`2026-11-13_g4_recovery_analysis_r02`|当前04的只读聚合；r01报告/代码快照保留|
|`2026-11-13_g4_recovery_verification_r01`|预算、原始输入完整性和16项receiver/network恢复序列核验|
|`g4_theory_20261113_v1`|有害刷新、SoD参考污染及隐私噪声同分布解析检查|

代码均在[code](code/)；运行需从仓库根目录使用`.venv/Scripts/python.exe`并传入全新Run ID。同seed重复或同seed内多个包不增加独立样本量。G3的正常fit、threshold、pilot分别使用原计划新种子，未运行confirm或Gate B。

文献证据按FULLTEXT/ABSTRACT/METADATA明确区分。本轮新增下载仅1份公开VoI作者PDF，来源和SHA256见[下载日志](sources/download_log.json)；其余全文为本地已有材料。原始Zotero附件未改动。
