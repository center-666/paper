# G1 Task 1.1：范围与来源审计

日期：2026-11-17。标记：FACT＝原文件或已保存数据直接支持；DERIVED＝明示假设下的推导；OPEN＝尚缺证据；HYPOTHESIS＝未验证假设。报告的NO-GO是提交负责人审核的建议，不替负责人决定研究路线。

## 1. 基线核对

**FACT。** 初始本地与远程冻结分支 g1r-e2-status-contract-20261115 均为 f9539c43037a9f5dc1596aed60ee45b679f9caee。已从该提交创建独立分支 g1r-task1-1-history-replay-boundary-audit；冻结分支没有移动。初始无已跟踪改动，仅保留此前G8/G9未跟踪草稿，不纳入本轮提交。不reset、不clean、不修改主工作区。

Task 1的20项文件SHA和Task 0.5的13项文件SHA均重新校验；核对方法及当前输入摘要见本目录 data/historical_candidate_summary.json、data/source_integrity.json。Task 0/0.5/1及原实验代码/结果均未改动。

## 2. 使用历史版本，不混用当前仿真器

历史源码在[Task 1证据目录](../g1_communication_behavior/task1/evidence/historical_five_node_v2)；下文行号均指该版本。

| 文件与行号 | FACT：实际行为 |
|---|---|
| sources/engine.py:37–40 | 节点发送参考/发送时钟、逐边raw缓存/接收时钟初始化 |
| engine.py:52–55 | 由pre-update估计和当拍本地量测形成Yang本地候选 |
| engine.py:59–73 | schedule=None启用平方距离严格大于.12或timeout≥10；k=0强发；先更新发送参考；节点广播复制到全部出边 |
| engine.py:76–90 | 仅fresh目标边可以替换；历史实现取同sender的第8个前序真实广播估计 |
| engine.py:108–125 | Yang权重1、无裁剪；收包刷新raw缓存和接收时间；按A的缓存年龄次幂对齐并融合 |
| sources/model.py:24–38、41–74 | 参数装配和全通信名义增益；SoD运行复用该增益 |
| sources/model.py:86–100 | 原模型过程/量测高斯噪声；本轮只读，不执行 |
| sources/run_study.py:131–153 | 配对共享testseeds及x/y；closed_loop传schedule=None |
| config.json | A=1.01I₂，Q=.02I₂，P₀=I₂，Hᵢ=(1,.8,1.2,.9,1.1)ᵢI₂，Rᵢ=.05I₂，ε=.08；五节点双向环；θ=.12，timeout10 |

这是一种Yang-form历史改编：所有节点每拍都有本地量测，硬SoD通信、raw缓存外推、冻结名义增益。不是完整复现Yang2014随机激活模型的所有假设，不能继承其全部稳定性定理。

## 3. 七项攻击核验

**FACT/DERIVED。**

1. 来源只取s<r且节点0真实发送的时刻；历史engine:84–88确实如此。
2. 实际模型按节点广播，故每条出边的发送时刻集合相同。0→1的历史发送集合等于节点0广播集合；首次注入前无攻击，旧估计也是该边当时真实发送的值。
3. r必须满足节点0真实发送；不能向静默链路伪造机会。
4. 发送判决→发送参考/时钟更新→目标载荷替换→接收raw缓存/时钟刷新→年龄对齐→估计k+1。
5. 替换在参考更新之后，不改变发送端参考。
6. Replay接收年龄归零；真实源年龄r−s仍可很大。二者不得混同。
7. 本轮理论是单包；历史归档200–249窗口实际每Seed9–33包、合计603包。只使用首次注入前历史及r+1首步评分，不把后续多攻击观测冒充新单包轨迹。

给定真实机会r：
\[
\mathcal T_j^{send}=\{t:S_j(t)=1\},\quad
\delta_{s,r}=\hat x_j(s)-\hat x_j(r),\quad
\mathcal D_r=\{\delta_{s,r}:s\in\mathcal T_j^{send},s<r\}.
\]
以时间标记的包列表应保留重复值；集合只合并相同向量。源码历史策略固定第8前序包，任务书的“所有先前真实包”是候选权限族，不能宣称历史runner已经执行了全族选择。

## 4. 原件、证据副本与新分析

| 输入 | 原件SHA256 |
|---|---|
| clean NPZ | 82f52b118a9a948c72771b39a636b63180114aef9449d67b03617234237bc16c |
| Replay NPZ（仅最初读取shape/有限性和来源） | ad92ba0f2974ce6189a76bd9d1d6897b62f711ed97639104e8142c09b381e766 |
| test_inputs.npz（仅最初元数据/有限性/Seed核查） | 8c247fda4fa66f984fd6545822edc904d09c258df6f247c784b46304e4ec2e80 |
| nominal_gains.npz | 7c636e9372461091c149818ab45a87b12920cccaff98669bf04b8388afbc0f33 |
| 历史engine.py | 766b58625775378405db110b4157d41b2700f8622f461383000d31fabd2cd508 |
| 历史model.py | d471643f273f119a1c934d1a79e83efcde3143244b6a491f65c740cb8a888d5d |
| 历史config.json | c71c687f13a6182f05d878bb0f0d171a36f0ca26afa09f2694b907674f3ac3ec |

原件位于主工作区 simulation/runs/2026-11-10_five_node_v2/，仅只读。为GitHub复核，clean NPZ和nominal_gains NPZ原字节副本保存在本目录evidence/。没有复制或生成新轨迹。test_inputs的x/y最初做过只读shape/有限性检查，后续公式和候选枚举不使用真值/量测；不把“算法未使用”错误写成“整个会话从未读取”。

候选复算入口为[分析脚本](code/analyze_historical_candidate_sets.py)。只导入NumPy等基础工具，读取既有NPZ/CSV/JSON；不导入engine/model、不调用simulate、generate_data、RNG或增益生成器。默认输出4个新分析文件；--verify只内存复算核对。所有结果是离线诊断，不是合法在线检测输入集合。
