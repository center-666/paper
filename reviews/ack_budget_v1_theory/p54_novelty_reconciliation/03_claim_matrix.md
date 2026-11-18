# P5.4主张—证据矩阵

该矩阵用于写作和审稿回复，防止把内部数学验收、物理支持和性能结果混成同一层级。

| 拟写主张 | 标签 | 可引用原始材料 | 可以说到的范围 | 不可以推出 |
|---|---|---|---|---|
| 每个长度L窗口最多B次有效阻断时，全失败机会的安全判据是窗口占用超过B | DERIVED | `02_t1_safety_characterization.md`；Badr 2013/2015作者稿模型页 | 固定机会集合、合法历史、单次截止、因果阻断 | ACK-V1独立首创；长期调度 |
| 连续尝试的最坏首次成功次数为$m^*$ | DERIVED | `03_t2_minimax_attempts.md`；`p5_evidence/20261109_internal_theorem_chain.md` | 持续请求、每时隙一次、可信即时ACK、硬预算 | 总发送/能源/MSE最优；所有随机策略 |
| 等待后连续尝试形成$m(s)$离散阶梯 | DERIVED | `04_t3_delay_cost_frontier.md`；`p5_evidence/20261109_internal_schedule_boundary.md` | 固定历史、截止任务、等待后连续后缀 | 时间戳前沿本身是首次创新；长期平均最优 |
| 原低/高请求锚点规则存在严格等待差距的参数充要条件是$B\ge2,\ L\ge B+4$ | DERIVED | `p52_reachability/03_reachable_states_and_proofs.md`；`data/summary.json` | 原规则、从空历史可达、符号通信自动机 | 任意触发器、任意网络拓扑或任意ACK策略 |
| P5.2有限闭包与Bellman复核通过 | FACT | `p52_reachability/05_validation_and_decision.md`；`data/regression_results.json` | L=2…14等明确范围；独立检查范围也有明确限制 | 对所有实现和所有无限参数的计算穷举 |
| 固定五节点Gaussian Yang模型中，P5.2严格差距离散状态具有正概率支持 | DERIVED | `p53_physical_support/04_positive_probability_theorem.md`；`07_final_decision.md` | 非退化Gaussian噪声、20边实际更新、指定因果贪心攻击、有限记录 | 概率大小/频率/长期出现/MSE改善 |
| P5.3覆盖 $B\ge2,\ L\ge B+4$ | DERIVED | `p53_physical_support/04_positive_probability_theorem.md`；六组完整见证数据 | 一般构造和有限网络参数 | 原稿B=2,L=5产生差距；普遍网络定理 |
| 完整记忆比立即发送更省通信 | FACT（条件实验） | `papers/paper2_ack_budget_deadline/manuscript/paper.tex` §实验结果 | 原指定攻击、50组、240拍、既定参数 | 一般通信优势；同精度优势 |
| 完整记忆在校准日历中优于普通触发 | 不能写 | `paper.tex`保存数字：普通128367次/MSE1.273858，记忆129982次/MSE1.277224 | 该结果支持反向限制 | 不得把单一贪心场景的节省推广为总体优势 |
| ACK历史+Bellman是本研究原创 | 不能写 | Sun 2026 TAC PDF8式(31)–(37)，PDF9 Theorem 3 | 只能说明本研究目标不同 | 不得宣称一般调度结构首次出现 |
| P5.2/P5.3已形成投稿GO | NO-GO | 本P5.4综合判断 | 当前档案和证据状态 | 不得用补充文献数量替代增量证明 |
