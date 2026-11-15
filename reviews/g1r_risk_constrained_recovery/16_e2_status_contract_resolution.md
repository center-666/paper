# 16 G1-R V2：E2状态合同修复与最终启动审计

日期：2026-11-15。隔离worktree由审计提交`490e5b8f1212004407a0cdbfde224bf90a691da4`创建，初始检出干净。Task5冻结实现和校准资产均存在于该基线。

## 结论

**状态合同已在独立适配层修复；原始算法、校准器、协议、门限及gate执行路径保持不变。** 30组缓存Debug输入比较的分数、proposal向量、raw status、证书、gate status和最终动作全部逐项精确相同。

**阶段A和B完成；E2/E3均未执行。** 最终证据包为[g1r_e2_status_resolution_20261115_r13](results/g1r_e2_status_resolution_20261115_r13/)。工作环境版本、BLAS、Task5冻结核心代码和补充列明的模型构造输入SHA均匹配；400个E2 Seed在已声明扫描范围内无历史冲突。Set校准199/199正常分数仍为零，冻结门限仍为零；这一方法风险留待正式E2检验。

**不建议现在启动E2正式数据运行。** 本轮完成状态合同、确定性验收和输入准备，但仓库中没有将冻结场景、200个Seed、24个事件年龄组合、在线proposal、离线评价和逐样本落盘串起来的E2正式运行器。E2 manifest仍是未执行模板。下一步应先实现并审计冻结协议的运行器；这不授权生成E2轨迹，正式数据仍需负责人另行批准。

## 1. 独立状态适配器

新增[e2_status_adapter.py](code/e2_status_adapter.py)，冻结估计器`v2_estimators.py`未修改。在线入口`propose_adapted(z, frozen_public_model, threshold, method)`的顺序是先检查输入，再调用原proposal算法。适配器保留原始Proposal对象，另算合同状态，并调用`apply_gate(raw_proposal, threshold)`。

状态规则：

|条件|raw_status|proposal_status|gate/action处理|
|---|---|---|---|
|z形状不是12维或含NaN/Inf|保留原返回值（若可产生）|INPUT_INVALID|仍记录原始gate状态；最终动作强制为零|
|公共矩阵无效|保留原返回值（若可产生）|MODEL_INVALID|fail-closed|
|raw VALID且证书zero flag为真|VALID|ZERO_OR_UNRESOLVED|gate仍用原score和阈值|
|raw VALID、非zero flag且门限前范数≤1e−12|VALID|ZERO_PROPOSAL|gate仍用原score和阈值|
|其他情况|保留|保留raw status|不改原gate|

测试覆盖Set零分离、零proposal、solver拒绝、正分数门限拒绝/执行、原始对象身份、非有限输入、错维度、非正定Sigma及无效事件矩阵。独立测试5项全部通过，见[adapter测试结果](results/g1r_e2_status_resolution_20261115_r12/adapter_tests.json)。预留E2 Seed未用于单测数据；日志示例采用虚构标识。

Task5结果中的Set正常分数为199/199个零，8个兼容候选均保留，分数界为[0,0]，没有空集合或solver拒绝；正常校准未保留逐样本创新和椭球，无法逐Seed追溯具体几何组合。既有Debug中的两例零分数也不是求解失败：Seed 141400000的8个候选椭球都含原点；Seed 141400003的前6个候选椭球含原点。详细支持函数诊断见[阶段A报告](14_pre_e2_readonly_audit.md)。这解释了零proposal的几何来源，但不意味着Set一定覆盖攻击污染或在E2中能采取足够多非零动作。

## 2. 原算法与门限等价性

最终等价Run：[g1r_e2_status_resolution_20261115_r05](results/g1r_e2_status_resolution_20261115_r05/equivalence_manifest.json)。缓存来自Task5已有Debug数据，原文件及本Run副本的SHA256均为`3d8137456ee2da019b2e18615f56166c6e6cef3c63fb0d19c59d0a8b28dfbd09`；未生成随机轨迹。

|比较字段|精确匹配|
|---|---:|
|score|30/30|
|proposal向量|30/30|
|raw status|30/30|
|数值证书|30/30|
|冻结gate status|30/30|
|门限后动作|30/30|

校准门限保持Hard 7.130518504393956、Soft 0.20737147161542802、Set 0。阈值文件SHA、Task5校准manifest及其中估计器/校准器/协议/矩阵/仿真源码SHA均匹配；没有重新校准。逐项结果见[proposal_equivalence.csv](results/g1r_e2_status_resolution_20261115_r05/proposal_equivalence.csv)。

## 3. E2日志和运行模板

[e2_log_schema.json](e2_log_schema.json)把raw status、派生proposal status、gate status、score、threshold、门限前/后范数、zero flag、兼容事件数及solver诊断分开保存。event、age和coverage只能由离线评价器在proposal/gate之后加入。Set集合覆盖独立于中心求解成功；攻击及正常非零率使用**门限后的实际动作范数**。正式统计要求每个冻结Seed恰好保留一行主场景结果，拒绝和求解失败均留在分母。

运行包位于[g1r_e2_status_resolution_20261115_r13](results/g1r_e2_status_resolution_20261115_r13/)：含缓存等价结果、状态映射统计、适配器/确定性/机制fixture测试、Schema、Seed扫描副本、环境快照、源码哈希、输入补充清单及E2运行manifest模板。模板状态为`TEMPLATE_NOT_EXECUTED`，未填负责人授权、启动时间、执行commit和E2结果；它不是实际E2 Run。R10的环境汇总曾因原校准manifest未列出两个补充输入而误报哈希不匹配；R11补齐了环境匹配，但尚未纳入完整源码哈希和Seed扫描副本。两者均保留，R13为最终核验包。

Task5原始校准manifest漏记的`simulation/config.json`和`simulation/reference_exploration_plan.json`见[model_builder_inputs_addendum.json](model_builder_inputs_addendum.json)。该文件明确标注为校准后的补充，SHA与Task5起始保护快照一致；原manifest没有被改写。

环境核验见[environment_freeze.json](results/g1r_e2_status_resolution_20261115_r13/environment_freeze.json)：隔离环境为Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1，BLAS完整描述与Task5校准环境完全一致。冻结Task5资产及共享engine/model hash也匹配。Seed扫描范围为当前可读取工作区文件、数组和归档；外部磁盘及备份不在覆盖范围。worktree由490e5b8干净创建；本任务的独立提交完成后，会再核验分支clean状态。未来E2 Run须在模板中填入获准执行时的最终代码commit SHA。

## 4. 启动审计答案

1. **状态合同通过**：ZERO_OR_UNRESOLVED和ZERO_PROPOSAL由独立层派生，原状态与gate状态均保留。
2. **原始算法完全保持**：冻结估计器文件hash不变，30组proposal/gate逐项零差异。
3. **校准门限完全保持**：使用Task5冻结阈值文件；未重新校准。
4. **日志可以区分状态**：零/未解析分离、求解拒绝、门限拒绝、实际执行各有字段；真实集合覆盖独立标记。
5. **运行环境准备已核验**：runtime、BLAS和冻结源hash与Task5一致；实际E2 Run仍是未授权模板，不冒称已经执行冻结。
6. **E2接口与证据条件通过，端到端启动条件未通过**：适配层、Seed合同、固定门限、运行时与记录Schema均可复核，但正式运行器尚不存在。
7. **最可能的E2失败风险**：攻击样本兼容集合仍包含零而导致Set动作稀少；真实污染落在集合外而使覆盖率不足；Set攻击非零动作数低于100/200。正常校准全零分数和零门限也不能预先确定正常测试误动作率。
8. **建议**：本轮不批准E2数据运行；只进入冻结运行器的实现和审计准备。运行器审计通过后再由负责人单独批准正式E2。

本轮已停止在E2正式实验之前。没有生成200条正常或攻击轨迹，没有使用E2 Seed，没有重校准，没有运行E3，也没有修改冻结算法、风险预算、事件字典或协议。阶段B确定性验收12项、状态适配测试5项和固定机制fixture均通过；它们只证明接口/数值/时序准备，不构成覆盖率、动作率或恢复性能证据。
