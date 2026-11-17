# Task 1.7：既有文献竞争审查

## 审查范围

**FACT。** 本表继承项目已有公式级材料，不重做大范围查新。本轮复核了仓库中的 reviews/fdi_replay_20261112/literature_reading_notes.md、reviews/distributed_filtering_security_privacy_literature/02_active_attack_literature.md、reviews/g6_retrospective_detection/01_research_direction_audit.md 和 reviews/g7_sod_conditioned_retrospective_detection/01_core_problem_audit.md；并核对本地保存的 Mustafa et al. 预印本文本。没有把搜索命中、摘要或“没有看到”写成全面不存在性证明。

## 公式与假设层面的竞争关系

| 文献/资产 | 攻击是否直接改变发送触发 | 估计—通信闭环、参考/缓存 | 历史Replay或历史攻击 | 实际结构与信息权限 | 对本任务的竞争结论 |
|---|---|---|---|---|---|
| Yang et al. 2014, Automatica 50(8), 2070–2076 | 否；随机Bernoulli激活 | 随机激活和邻居估计融合；非本任务硬SoD发送参考/raw缓存年龄规则 | 否 | 式(1)–(11)、Theorem 1为随机激活估计及协方差/稳定性 | 给出底层分布式估计背景；其定理不能直接移用于SoD闭环攻击 |
| Han et al. 2015, TAC, DOI 10.1109/TAC.2015.2406975 | 随机触发，不是攻击诱导 | 随机阈值、条件更新；Gaussian闭合 | 否 | 指数二次非发送概率，Theorem 1及式(26)–(42)得精确Gaussian更新 | 条件选择统计已有理论；与本项目硬指示触发分布不同 |
| Qian et al. 2023, TAC, Event-Triggered Distributed State Estimation: A Conditional Expectation Method | 非安全攻击问题 | innovation触发并使用非发送信息 | 否 | 式(3)–(4)、Lemma 1和Theorem 1处理条件期望/截断二阶矩，含Gaussian近似假设 | “事件条件会改变估计统计”不是新发现；其具体估计器不等于本Yang缓存实现 |
| Qiu et al. 2019, TIE, A Tradeoff Approach for Optimal Event-Triggered Fault Detection | 研究触发与检测设计耦合 | 触发误差进入残差，不是本任务邻居raw缓存Replay | 非本任务单包历史Replay | 式(2)–(7)、Theorem 3.2的H∞检测设计与阈值 | “触发误差需计入安全/故障残差”已有直接先例 |
| Liang–Liu 2023, TIM 72, 3520111 | 事件机制存在，攻击/故障作用于通信/物理信号 | 事件触发ZOH、UIO邻居残差 | 不是共同状态Yang的旧邻居估计包Replay | 式(18)、(28)–(30)，Theorem 1–2为UIO及检测/隔离条件 | 事件通信保持值与检测残差已有先例，架构和攻击字段不同 |
| Mustafa, Mazouchi & Modares 2021, Secure Event-Triggered Distributed Kalman Filters…, arXiv:1901.06746v4, pp.4–9, Theorems 2–5 | **是。** Theorem 2构造non-triggering；Theorem 3使用Replay后再eavesdropping实现continuous-triggering | 事件变量控制预测估计发送/保持；接收估计由本地量测更新及邻居估计融合。不同于本项目发送参考、raw接收缓存及A^age更新次序 | 有Replay攻击构造，但不是被动替换单条链路上一份真实邻居estimate的同一威胁模型 | 式(3)按当前量测与预测输出触发；Theorem 2/Remark 3要求攻击者能访问实际量测及最近发送先验；检测式(30)–(42)、Theorems 4–5用滑窗kNN-KL识别传感器/链路；Theorem 6给trust融合误差有界条件 | **最接近的竞争者。** 直接否定“攻击改变事件触发/通信行为”这一宽泛创新。具体单次缓存包权限和Yang-form同步缓存模型是差异，但尚未导出超出切换系统代数的定量新结果 |
| Huang et al. 2024, TCyb 54(6), 3526–3539 | 不是本任务SoD发送参考反馈 | 分布式consensus filter | 是，循环Replay测量片段 | Theorems 1–7研究量测Replay下误差协方差、残差/KL隐蔽性 | Replay检测已有强先例；其对象是传感器测量片段而非邻居估计缓存 |
| Su et al. 2022, IEEE Systems Journal 16(4), 5720–5728 | 不同通信机制 | 安全sensor/多sensor观测器与隔离 | 是，多sensor测量Replay | 使用packet label和可信sensor假设 | 不能作为同权限基线；但排除“Replay本身无人研究” |
| Xing et al. 2025, TIFS 20, 4541–4550；Ge et al. 2026, TCyb, DOI 10.1109/TCYB.2026.3721072 | 不等价的SoD发送状态闭环 | 历史创新攻击通过协方差传播影响分布式估计 | 是，攻击历史innovations | KL/χ²隐蔽约束、历史攻击矩阵及拓扑约束 | 历史攻击与误差传播不是空白；攻击载荷与本任务权限不同 |
| Task 0/0.5 与 G1-R | Task 0.5中观察到Replay后SoD事件不同 | Task 0.5归档SoD闭环；Task 0提供已有缓存分叉恒等式 | 历史归档实际每Seed多次Replay | 32/32节点1出现事件差异；不是新的独立单包确认实验 | 是本任务的研究资产与模型动机，不是独立于历史结果的新实验 |

## 创新边界

**FACT。** 已有文献分别覆盖随机/事件触发分布式估计、触发条件统计、触发误差检测、攻击改变事件发送、攻击诱导的通信异常，以及历史Replay/innovation攻击。Mustafa等人的攻击能力较本任务强，系统机制也不同；这种差异需要逐项比较，不能忽略，也不能简单说对方已完整解决本项目。

**DERIVED。** Task 1新增的工程价值在于严格按本项目执行顺序，把触发裕度、发送参考、边缓存raw值、接收年龄对齐与Yang更新做两轨迹相减。其公式正确且比只写估计污染更完整。但命题一仍是平方范数展开和布尔OR分叉判据，命题二仍是缓存/参考重置方程相减；本轮没有给出Replay合法来源约束特有的分叉时间界、模式切换稳定性条件、信息论检测保证，或同权限性能优势。

**OPEN。** 现有审计不是对全领域所有论文“未解决”的证明。若负责人要求论文立项，必须先明确一个这样的定量命题并补足直接竞争文献；本轮按Task 1门槛不建议继续扩大文献搜索或先开发检测器。
