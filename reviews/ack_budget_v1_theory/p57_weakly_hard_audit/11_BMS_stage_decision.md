# P5.7-B：BMS 阶段裁决与反向审稿

日期：2026-11-18。基线 de807527af90f2040e9402fafedc6287dbababa1；分支 ack-v1-p57-weakly-hard-audit。FACT 为原文或冻结资产事实，DERIVED 为本轮证明/评估，OPEN 为未关闭的证据缺口。此文件只裁决 B 阶段，不给 P5.7-C/D/E 或 P6 授权。

## 1. 总体裁决：PARTIALLY COVERED

**DERIVED。** 这不是“BMS 与 ACK 只有名称不同”，也不是“找到差异所以原创成立”。应分层记录：

| 层次 | 判定 | 具体证据 |
|---|---|---|
| 历史成功/失败窗口、跨成功保留旧失败、以历史位置计算失败余量 | **COVERED** | BMS 29 页定义 2、LSH；30 页式 (1) |
| 连续首成功保证次数对应的数值距离及其等待后更新 | **COVERED，限定数值函数** | 本轮严格证明 m*=δ+1；带截止的 m(s) 见 09 报告 (M1)–(M2)。不是说原文已写出 ACK 全策略 minimax 博弈 |
| 临界时提供保证服务；有 slack 时延后进入保证模式 | **COVERED，机制层** | 原文 32 页 §5/图 1 的 delayed panic，33 页推论 1；不能再作为独立算法创意 |
| 固定截止等待公式及其原始网络解释 | **PARTIALLY COVERED** | 同为截止减去保证完成需求；精确网络余量还需预算语义，但 P5.6 已将该公式降为基础命题，维持不变 |
| 原协议临界禁 101、全参数严格差距分类 | **NOT DIRECTLY COVERED** | 10 报告给出 BMS 合法而原 ACK 禁止的 101，以及局部合法但不可达的差距状态；已核定理没有原门控闭包量词 |
| 某一特制 BMS normal 策略是否可与 ACK 完整双模拟 | **OPEN** | 可以加入状态/输入并特化正常策略，但本轮没有建立这一完整映射；不能把可编程性当成已有分类证明 |
| 整个 P5.7 的新颖性与独立论文价值 | **OPEN** | C/D/E 尚未审；B 的不直接覆盖不等于 NOVEL，更不等于达到学报增量要求 |

**FACT。** B 文献正式全文及哈希已核，状态为 FULLTEXT。此前 BMS、criticality、delayed panic mode 的术语缺口已经关闭：它们均确实出现在本篇原文。不能再将 B 仅标为摘要证据，也不能保留“该领域未提出历史驱动安全延后”这种过宽措辞。

## 2. 三个核心结果的答复

**DERIVED。**

1. **禁 101：** BMS 通用框架允许 normal 策略在 δ>0 时跳过调用。一个 any(3,5)、T=D=1、C=1/2 的单任务例子，从原初始化热身后产生 μ=010，即 β=101，且临界调用均完成。原 ACK 在相应第三拍必须等待。这个单步反例排除了直接套用 BMS 通用定理得到 ACK 禁串。
2. **参数分类：** BMS 的预算合法字可以对应 B=2,L=5 下 H={1,3} 的形式状态，具有 s_safe=1、s_cost=0；原 ACK 恰因禁串排除它。故只凭 BMS 的窗口保证不能把形式状态集合变成原协议可达集合，也不能直接推出 B≥2,L≥B+4 的分类。
3. **从空历史的构造：** BMS 能安排相同的合法结果字，并不等于已经证明原高低请求、真实尝试、反应式阻断和自然锚点产生该字的同一机制。P5.2 的门控一致性步骤仍是额外工作；这些步骤也可能只是一个很短的协议特化分析，不能单凭存在它们就认定创新。

完整构造、假设与每步计算见 [10 报告](10_BMS_equivalence_and_counterexamples.md)。没有靠“没有相同公式”或标题差异作结论。

## 3. 严格审稿人的五项质疑

### 3.1 状态压缩是否只是普通在线状态机？

**DERIVED：这项质疑成立。** 失败年龄队列相当于已知移位寄存器，锚点年龄是一个有限计时器。BMS 已明确保留历史并在释放时据此决策。状态压缩有工程和证明用途，但不足以构成新的控制理论或算法贡献。仅指出“多了一个锚点变量”不能应对排重。

### 3.2 禁 101 是否只是简单门控不变量？

**DERIVED：证明复杂度上的质疑成立。** 临界时一拍失败、下一拍非失败建立锚点、再下一拍因旧失败占额而必须等待，确实是短的局部不变量。它有助于正确排除形式状态，但单独不足以支持论文。它只能作为全参数分类中的必要步骤，不能包装成普遍的安全估计定理。

### 3.3 充要分类是否只是有限窗口计数的组合推论？

**DERIVED / OPEN。** 当前证明由 B≤1、短窗、临界窗的计数排除和一条参数化见证组成，没有新的证明工具。一般整数参数的充要性比有限枚举更完整，但“证明一般性”不自动意味着研究增量足够。已核 BMS 定理不能直接给出它；然而在给定原门控后，分类仍可能被审稿人视为标准窗口推理的专门推论。这个新颖性强度风险保持为高。

### 3.4 Gaussian 支持是否只是嵌入已知调度序列？

**FACT。** P5.6-C 已保存指定 Gaussian 网络与固定原协议下的有限时域下界：P(E_2,6)>0.00061509375、P(E_3,7)>0.0002767921875。不能把现有资产退回“只剩极小开球”或忽略已核定量结果。来源：[P5.6-C，C1](../P5.6_C_gaussian_physical_relevance.md)。

**DERIVED。** 但它仍是指定物理网络对特定离散协议事件的支持，不是高频出现、长期收益或更优 MSE 的保证。利用非退化 Gaussian 支撑实现有限严格不等式事件，是一般思路；模型特定的量化工作可以保留，却不能自动挽救已知调度机制的新颖性。BMS 不含这个 Yang 嵌入，不等于嵌入本身已成为独立控制贡献。

### 3.5 控制领域价值是否足够？

**FACT。** 已有主实验 B=2,L=5 属于无严格差距区域。日历攻击下独立阈值校准的普通触发基准为 128367 次尝试、MSE 1.273858；原候选为 129982 次、1.277224。原候选在该比较中两项均不占优。来源：[P5.6-D，D1/D3](../P5.6_D_theory_experiment_alignment.md)及其引用的正式结果；本轮未重算或替换指标。

**DERIVED / OPEN。** 性能优势不是理论论文的必要条件，但仍需要一个能改变设计判断、具有足够普适性或结构解释力的理论问题。目前能够诚实留下的是“这个固定门控在什么参数下会访问安全等待与最坏首成功成本冲突的状态”，不是普遍更优的分布式估计或发送算法。现有证据不足以从“BMS 没有直接分类”跨越到“已足以独立支撑控制学报论文”。

## 4. BMS 原文的局部严谨性边界

**DERIVED。** 本轮发现：定义 3 列举的四条性质单独不足以证明定理 1，必须使用连续失败距离的准确语义/一步安全条件；计数型式 (1) 可严格补足。miss-row 文字、式 (3) 和未来模式存在一拍不一致，meet-row 的 γ 也有参数次序疑点。这些均在 08 报告原式、页码及反例旁单独记录。

**DERIVED。** 这些问题不能被用作“否定 BMS，所以 ACK 创新”的捷径。与本项目对应的 any(n,m) 距离和延后保证机制仍有明确原文与可补足的数学证据。需要的额外假设必须列出，而不是静默修补整个 BMS 或将它说成完全不可用。

## 5. 本轮交付与保护核验

**FACT。** 本轮只新增以下四份 Markdown，旧 08_A_review_evidence_and_integrity.json 保持原名和原内容：

- [08_BMS_fulltext_and_theorem_extraction.md](08_BMS_fulltext_and_theorem_extraction.md)：系统、criticality、两种模式、全部编号保证及证明依赖。
- [09_BMS_ACK_mathematical_mapping.md](09_BMS_ACK_mathematical_mapping.md)：三种编码尝试、距离等式、双向模拟边界。
- [10_BMS_equivalence_and_counterexamples.md](10_BMS_equivalence_and_counterexamples.md)：三个候选结果的反例及因果性检查。
- 本文件：总体判定、反向审稿、证据缺口和停止点。

全量旧文件核验范围为 Git 受跟踪文件及本轮开始时的 9 份 P5.7 本地草稿，不把 .git 元数据、忽略的运行缓存或仓库外论文算作研究源文件。最终结果如下：

**FACT - final integrity verification.**

| Check | Result |
|---|---|
| Verified at (UTC+08:00) | 2026-11-18T19:34:55.660601+08:00 |
| HEAD / P5.6 branch | de807527af90f2040e9402fafedc6287dbababa1; unchanged |
| All pre-existing tracked + stage-local files | 35175 files; 467045764 bytes; every SHA256 unchanged |
| Pre/post path-and-SHA256 tree digest | fcabb847eee9dbf9242a5310c6cf78746215e40b2544033f949b3343eeda0823 |
| Source B SHA256 | 2e5512e02e81857b28695250f9d53919b5ea0f1a52e2ded7f477b8291f5c8d06; unchanged |
| Existing P5.7-0/A drafts | 9; byte-for-byte unchanged |
| New files | Exactly the four requested B-stage Markdown reports |
| Tracked Git diff / staging area | Empty / empty |
| Relative report links checked | 15 |
| Python computation | Fixed integer examples only; no simulation, random samples or graph sweep |
| Commit / push / C-D-E / P6 | None |

Local per-file hash snapshot (outside repository): C:/Users/zhongxin/AppData/Local/Temp/ack_p57_B_old_file_hashes.json. The aggregate uses sorted paths, NUL separators before SHA256, and LF separators between rows.

## 6. 停止与未解决项

**OPEN。** 尚未建立：某个已发表 BMS 特化正常策略与原 ACK 的完整因果双模拟；其他已指定文献对同一分类的覆盖；这一专门分类独立支撑目标期刊的充分增量。此处不是请求追加新算法或实验。

**本阶段已完成并停止。** 不启动 C/D/E、不启动 P6，不恢复 C1，不修改正式稿，不推送。后续是否继续剩余文献排重，由负责人审核决定；本轮的 NOT DIRECTLY COVERED 不作为 NOVEL 或投稿许可。
