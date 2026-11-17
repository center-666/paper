# ACK-V1 P5.2：安全等待与最坏尝试成本的可达性审查

日期：2026-11-17。基准提交：80f235c9aed754deb47b53c4e010c2424279ea0d。
交付分支：ack-v1-p5-2-reachability-audit。
FACT＝来源或已完成的验证直接支持；DERIVED＝明示假设下的推导；OPEN＝尚未解决。

## 给研究负责人的结果

1. **FACT：两项全文缺口已补齐。** Dolk 第5章和 Lu 2026 的16页正式PDF已逐式核对。前者在 Zotero；后者实际位于用户 Downloads，Zotero 当前附件仅是网页。没有把网页当全文，也没有改动 Zotero 或上传第三方PDF。见[来源与对照](01_fulltext_addendum.md)。
2. **DERIVED / 已验证：给定 B=2,L=6 反例成立。** 原规则可以到达 k=6、H={1,4}、τ=5、D=8；立即发送最坏1次，等一拍最坏2次。这是安全与成本边界不同，**不是旧安全定理错误**。见[逐拍核验](02_counterexample.md)。
3. **DERIVED：一般参数分类。** 在原规则、空历史、允许低偏差自然锚点的单边通信自动机中，存在可达状态满足 s_safe>s_cost，当且仅当 B≥2 且 L≥B+4。证明不依赖有限枚举。特别地，旧稿 B=2,L=5 的全部可达状态两边界相等。见[定理与证明](03_reachable_states_and_proofs.md)。
4. **DERIVED：成本中性在线规则成立。** 高请求时仅当 s_cost≥1 才等待，否则发送；可靠ACK更新历史。它保持原锚点截止，且对当前固定截止的持续请求任务，最坏首次成功尝试次数恰为初始 m*。这不等于长期通信量、能耗或真实MSE最优。见[规则与保证](04_cost_neutral_rule.md)。
5. **FACT：有限验证通过。** 104组(B,L)，两规则143,712个可达状态、394,243条转换；原规则60,177个状态中2,646个严格差距状态，分布于45组参数。另有独立位掩码图、绝对时间Bellman和8项回归验证。第一次测试中错误预期“案例数>1000”，实际559；已保留问题并校正计数，未删案例或放松数学判据。见[验证及限制](05_validation_and_decision.md)。

## 阶段决定与唯一后续入口

**DERIVED：P5.2 在声明的通信模型中通过数学审查，供负责人验收。**
这不是论文立项通过，也没有证明文献首创；T1仍是基础引理，T2/T3仍需保留内部2026-11-09成果归属。

**OPEN：** 更紧的历史条件估计误差保证、实际闭环平均通信收益及MSE收益均未建立。
建议负责人审核这些结果后，决定是否单独授权 P6 的误差动力学可行性推导。本轮到此停止，不执行 P6、不修改旧正式稿、不运行Monte Carlo、不改变任何估计器或旧实验。

## 可审阅资产

- [文献补充](01_fulltext_addendum.md)、[反例](02_counterexample.md)、[一般分类](03_reachable_states_and_proofs.md)、[在线规则](04_cost_neutral_rule.md)、[验证与决定](05_validation_and_decision.md)。
- [参数逐项表](data/parameter_summary.csv)、[验证摘要](data/summary.json)、[最短反例见证](data/shortest_gap_witnesses.json)、[回归结果](data/regression_results.json)。
- 完整状态和转换：data/reachable_states.jsonl.gz、data/reachable_transitions.jsonl.gz（确定性 gzip，可解压为逐行JSON）。
- [通信自动机代码](code/reachability_audit.py)、[独立验证代码](code/test_reachability.py)、[完整性工具](code/verify_integrity.py)。
- integrity_manifest.json 记录本包除清单自身外全部文件SHA256；data/protected_assets.json 记录旧资产SHA256及Git blob基线。清单不自包含，Git提交固定清单本身。
