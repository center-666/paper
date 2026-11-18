# 来源、模型假设及证据边界

日期2026-11-18。下面均为 **FACT**，理论推导的具体条件在各报告注明。

## 1. 本轮授权与基线

- [负责人审阅原文副本](data/research_lead_review.txt)：P5.2有条件验收，先P5.3再P6.1—P6.4，不改正式稿、不启动大规模实验；本轮进一步采用零仿真。
- 基准提交320744ea77e3f8637980d083e3365d255ac3bb79，原分支ack-v1-p5-2-reachability-audit；开始时本地/远程一致、工作区干净。另建ack-v1-p53-p6-theory-feasibility。
- 用户已授权结果上传GitHub；只提交新目录，不修改任何旧报告。

## 2. 直接数学与代码来源

| 来源 | 核查位置 | 用途/限制 |
|---|---|---|
| [旧paper.tex](../../../papers/paper2_ack_budget_deadline/manuscript/paper.tex) | 71—90行eq:system/eq:parameters/eq:yang；95—150行时序/缓存/锚点；239—305行eq:error、eq:matrix、eq:comparison | 本轮唯一物理参数和估计更新基线，非用户更早贴出的另一份MATLAB参数 |
| [冻结节点表](../../../papers/paper2_ack_budget_deadline/manuscript/certificate_table.tex) | Nodes与Coordinate RMS/Node MSE bound | 固定矩阵复算参考；不是条件风险表 |
| [P4.5量词审查](../07_independent_proof_audit.md) | 共同模型、T2、T3 | 真实尝试、因果守卫、包含成功尝试的成本 |
| [P5定位](../12_p5_novelty_risk_and_positioning.md) | 内部2026-11-09成果及风险 | 不重复宣称T2/T3首次发现 |
| [P5.2一般分类](../p52_reachability/03_reachable_states_and_proofs.md) | 命题1、定理2、§6 | 继承通信自动机分类；P53补其概率OPEN |
| [P5.2成本规则](../p52_reachability/04_cost_neutral_rule.md) | 定理3、§4 | 锚点与单任务成本保证；确认公共证书接口 |
| [P5补读](../p52_reachability/01_fulltext_addendum.md) | Dolk/Lu的模型、公式、风险定位 | 不新增文献搜索，不混淆MANSD、概率预测与硬物理窗 |

原calendar派生引擎在主工作区：
C:\Users\zhongxin\shixidoc\mypaper\第二篇小论文\第二篇小论文\韧性恢复\fusion_network_20261104\ack_calendar_validation_20261108\engine.py。
只读检查simulate、42—47行预测/触发、53—87行发送/ACK/缓存/锚点、100—117行同步新估计及误差身份。参数文件为同级上层ack_paired_feasibility_20261107/运行前固定.json。
该引擎是相关calendar派生版本；继承P0关于“未逐字节追溯全部最终实验源码”的限制。本轮没有导入或执行其simulate，也不把此读码称为重新验收全部历史实验。

## 3. 防止重新走回旧失败路线

已读取主工作区fusion_network_20261104/AGENTS.md、研究目标_长期约束.md，及ack_final_asset_audit_20261109/全阶段成果审查与冻结结论.md。其中早期方向安排有历史变化；当前用户本轮附件的P53/P6权限优先，旧冻结结果和禁止夸大性能的约束继续继承。

[旧邻居相关性审查字节副本](data/prior_correlation_boundary.md)来自neighbor_correlation_gate_20261106/邻居信息相关性_可见评价与Gaussian增益路线收束.md。§2—3已给可见交叉矩评价和选择偏差限制；§4以后说明预算计数未给有利符号，不把旧Gaussian增益路线当成获准重启。
副本保留原相对链接作为历史证据，部分链接在新目录不解析；不修改副本修补历史内容。新报告需要的判断已引用具体章节，源SHA记data/source_manifest.json。

## 4. 模型假设边界

- 固定Yang型增益加逐边ACK预测缓存扩展，不宣称复现Yang2014原始最优随机激活协方差算法。
- 物理状态不受调度控制；新噪声独立、R非退化。若加入反馈控制或退化噪声，P53全支撑与集中参考需另证。
- 每边独立硬预算不等于攻击决策独立；协调攻击者仍可依赖发送向量和过去ACK。
- P53只指定一条目标边有限记录，其他边真实闭环；没有证明任意20边联合符号输入都物理可达。
- µ、Σ的集中条件公式是分析oracle；单节点看不到全网私有量测，不能据此实现调度。
- 旧公共证书为总体期望，精确条件公式为同一固定策略下的正则条件期望；不混同量词或比较基准。
- 首成功成本、长期通信成本、真实MSE和检测性能始终分开，本轮不研究新检测/恢复算法。

## 5. 完整性与来源清单

data/source_manifest.json 记录已读主工作区文件和附件的SHA256；两个用户自有文字证据仅以副本加入本包，原件保持。
data/protected_assets.json 记录基准中ACK审计、旧ACK稿及simulation关键文件的Git blob和SHA；完整性工具还检查所有已跟踪包外文件与基准无差异。
本包integrity_manifest.json覆盖除自身外全部新增文件；清单自身由Git提交固定。无第三方PDF上传、无旧实验数据搬迁。
