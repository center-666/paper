# 方案A与既有恢复方法：全文及项目证据核查

日期：2026-11-14。范围仅限Tabatabaei 2025、Deghat 2019及项目已有GLS/回滚/平滑基线。本轮未下载论文、未生成轨迹、未修改旧实验。

标记：`LITERATURE`为原文已有；`PROJECT`为旧代码/旧结果；`DERIVED`为本轮分析；`OPEN`为尚未解决。以下页码均为**本轮实际读取的出版社PDF页码**。旧Deghat作者稿为14页、旧Tabatabaei归档含封面为14页，不能直接沿用其PDF页码。

## 1. 来源与核查范围

原始文件来自用户Zotero：

|文献|本地附件|版本、页数与索引|
|---|---|---|
|Tabatabaei, Gallo, Al-Dabbagh. *Secure state and output estimation for accommodation of false data injection attacks in large-scale systems*. Automatica 180 (2025), 112460. DOI 10.1016/j.automatica.2025.112460|`C:/Users/zhongxin/Zotero/storage/VTR8LLKB/`内PDF|出版社13页；抽取文本`prior_tabatabaei2025_publisher.txt`本地保留|
|Deghat, Ugrinovskii, Shames, Langbort. *Detection and mitigation of biasing attacks on distributed estimation networks*. Automatica 99 (2019), 369–381. DOI 10.1016/j.automatica.2018.10.052|`C:/Users/zhongxin/Zotero/storage/P2BTH2ZJ/`内PDF|出版社13页；抽取文本`prior_deghat2019_publisher.txt`本地保留|

完整文件名、SHA256及抽取文本哈希见[来源索引](prior_source_index.json)。复核原模型、算法、假设和相关定理及证明；不是只使用摘要或先前报告。

## 2. Tabatabaei 2025：已具备攻击重构、误差补偿和恢复

### 2.1 原始系统与攻击入口

`LITERATURE`：出版社p.2式(1)–(2)为连续时间、具有**物理耦合**的异构子系统：

\[
\dot x_i=A_ix_i+B_iu_i+B_{ci}\bar x_i,
\quad y_i=C_ix_i,\qquad
B_{ci}\bar x_i=\sum_{k\in\mathcal N_i^p}A_{ik}x_k.
\]

p.3式(3)攻击的是控制协作链路传输的邻居**传感器输出**：
\(\tilde y_{ki}=y_k+\Gamma_{ki}\)，不是Yang网络共享同一个物理状态的邻居滤波估计。式(4)还给出由邻居过程模型驱动的covert攻击。

这项架构差异不是创新证据。关键是原方法利用哪些独立约束、给出什么保证，以及在当前协议中这些约束是否真实存在。

### 2.2 方法、假设和定理

|原文定位|内容及真正保证|
|---|---|
|p.3 Assumption 2.1；p.4 Assumptions 3.1、3.2|局部\((A_i,C_i)\)可检测、\((A_i,B_i)\)可控；接收节点知道邻居过程及物理耦合模型；UIO要求相应扩展矩阵满列秩及\(\operatorname{rank}(C_kB_{\varsigma k,i})=\operatorname{rank}B_{\varsigma k,i}\)|
|pp.4–5式(6)–(11)|先以UIO构造误差/残差，再将攻击及其一阶导数增广为状态，Luenberger型观察器重构误差及攻击；式(9)外输入\(\bar\Gamma_i=\ddot\Gamma_i^t\)|
|p.5 Assumption 3.3；Theorem 3.1、式(12)–(15)|排除不受观测的零模态污染，相关可配极点稳定，非隐蔽FDI且\(\ddot\Gamma_i^t\to0\)时，\(\hat x^r_{k,i}=\hat x_{k,i}+\hat\epsilon_{k,i}\)、\(\hat y_{ki}=C_k\hat x^r_{k,i}\)、\(\hat\Gamma_{ki}=\tilde y_{ki}-\hat y_{ki}\)渐近重构状态、真实输出和攻击|
|p.6 Algorithm 1、Theorem 3.2及式(16)–(18)|以重构输出代替可能受攻的邻居输出用于控制。证明使用三角误差系统及稳定矩阵；\(\bar\Gamma\)有界得到有界性，\(\bar\Gamma\to0\)得到相应渐近恢复。原定理表述中的渐近稳定不能解读为任意持续非零有界\(\bar\Gamma\)均使状态趋零，证明明确区分这两种情形|
|p.7式(20)–(24)、Assumption 4.1、Proposition 4.1；p.8式(25)、Props.4.2–4.3|对隐蔽攻击，利用可信本地\(y_i\)和物理耦合重构\(\bar x_i\)；\(\ddot{\bar x}_i\to0\)等条件下渐近成立。各耦合像空间可分及相关满秩条件决定邻居状态完整或部分可重构|
|pp.8–9 Theorem 4.1、式(26)–(29)|将可重构邻居的安全输出送入控制器，分析BIBO及H∞能量性能；仍是连续过程/观察器条件，并非有限样本误报警或随机滤波MSE风险|
|p.9 Props.4.4–4.6、Algorithm 2|比较由可信物理通道和可能受攻通信构造的估计，给出隐蔽攻击检测、链路隔离及协调攻击无法检出的边界|

`LITERATURE`：原文没有把攻击开始时刻、攻击结束时刻或攻击值作为在线观察器输入；\(T_{ai}\)出现在Assumption 3.3的分析初值条件，不等于部署时必须输入已知攻击时刻。因此不能把“我们未知攻击时刻、对方已知”作为区别。

`LITERATURE`：没有要求先报警才启动重构，观察器持续运行；攻击停止后其估计/修正动态仍继续，因而不能宣称该文不处理任何攻击后污染。但它没有提出：离散缓存已退出的接收事件有限样本候选置信集、不同事件映射成当前影响集合、同正常误补偿预算的拒绝/部分补偿策略。

### 2.3 能否直接解决方案A？

`DERIVED`：**不能直接继承全部方案A，但已覆盖“重构估计误差并补偿、实现名义恢复”的大部分基础能力。** 当前Yang网络没有对应的物理耦合\(A_{ik}x_k\)独立证据，噪声和缓存切换也不符合原连续无噪声过程模型。需要重新建立可检测性、噪声统计与离散缓存输出模型，不能靠换变量直接得到方案A的有限样本集合覆盖与误补偿风险结论。

`OPEN`：上述缺失不自动证明方案A创新。集合构造及选择性补偿还必须与标准多模型集合估计、选择性决策及同权限平滑比较；不能只用该文的模型差异获得Go。

## 3. Deghat 2019：不仅有修正，也明确提出阈值切换输出

### 3.1 原模型与攻击权限

`LITERATURE`：出版社pp.2–3式(1)–(4)：共同连续物理过程，各节点以本地创新和**当前实时邻居估计**更新；攻击作为\(F_if_i\)进入观察器动态。p.3式(4)后明确说明链路偏置可取\(F_i=K_iH\)，因此不能因其主记法为节点输入就排除链路攻击竞争。

pp.3–4式(5)–(11)：允许偏置/暂态及有限能量攻击，构造满足\(f_i=\hat f_i-\nu_i\)、\(\nu_i\in L_2\)的辅助输入跟踪系统。攻击形状和渐近值未知。单次有限能量Replay差可属于其攻击输入类，但本项目持续随机白噪声、间歇缓存及离散增益条件不由此自动满足。

### 3.2 方法与理论

|原文定位|算法/结论|
|---|---|
|p.4式(12)–(13)|本地创新\(\zeta_i=y_i-C_i\hat x_i\)和邻居分歧\(\bar\zeta_i=\sum_jH(\hat x_j-\hat x_i)\)|
|p.5式(14)–(20)|增广误差与攻击模型，分布式H∞观察器式(18)估计\(e_i\)及辅助攻击状态；还需邻居辅助误差估计\(\hat e_j\)交换，不只有原\(\hat x_j\)消息|
|pp.5–6 Problem 1、式(21)–(22)、Theorem 1|内部稳定，L2扰动下攻击跟踪误差能量界；附加条件下渐近跟踪。证明由H∞能量及稳定动态/L2导数推出渐近性质|
|pp.6–7式(24)–(29)、Theorem 2|向量耗散、耦合连续LMI设计检测器增益；存在LMI可行性和噪声通道非退化条件|
|p.7式(30)、Theorem 3|修正输出\(\hat{\hat x}_i=\hat x_i+\hat e_i\)，满足前述设计时的弹性估计/能量保证；不是仅估计攻击值而没有状态恢复|
|p.8 Section 5、Theorem 3后讨论|明确承认正常情况下修正观察器可能劣于原观察器，并建议用threshold-based policy在原输出与resilient输出之间切换，门限设计指向故障检测文献|
|p.8式(31)–(34)、Theorem 4|将攻击增广可检测性与网络/传感器/攻击入口子空间联系；不是任何网络无条件可检测|

**关键竞争纠正：** `LITERATURE`，p.8原文明示：

> A threshold-based policy can then be devised to switch the observer outputs from the original estimates ... to the resilient estimates ...

因此“报警后才修正”“无攻击保留原输出”“避免正常修正损失”的基本动机和切换操作都不是方案A首次提出。其式(30)本身也是修正输出，不要求改写原滤波器内部状态。

### 3.3 对方案A仍未直接提供什么

`DERIVED`：未发现原文构造过去链路接收事件\((e,r)\)的有限样本覆盖集合，未把多事件影响并集作为优化对象，也未给\(P_0(\text{触发})\le\alpha\)、有界补偿量及真实正常MSE增量之间的概率预算。该文已有连续H∞风险意义，但不是本方案拟议的随机MSE/误归责损失保证。

`PROJECT`：此前[09号适配审计](../../g1_retroactive_recovery/09_deghat_discrete_baseline.md)仅完成结构映射，未完成忠实离散性能复现。需要辅助消息、离散缓存设计和相应证书的事实仍成立。本轮不把普通GLS冠名为Deghat、不做胜负排名。

## 4. 必须修正附件中的项目现状描述

### 4.1 早期已知事件与最终未知事件不能混同

`PROJECT`：早期P0/5seed影子和联合回写使用预先指定\((0\to1,200)\)，但之后已有接收端实际记录驱动的未知事件接口及100seed最终独立测试：

- [receiver_gls_writeback.py](../../g1_retroactive_recovery/code/receiver_gls_writeback.py)：`candidates_from_receptions`枚举真实入边接收事件；`fit_full_prefix`使用正常训练/独立校准创新；`attribute`对候选GLS分数取最大值，不输入真实事件、真状态或原始未篡改包。
- [final_replay_run.py](../../g1_retroactive_recovery/code/final_replay_run.py)：`records`、`innovation`、`fit_for_gap`、`writeback`和主循环完成未知归责至修正的接线。真实事件仅用于oracle及离线正确性评价，不能混为恢复器已知输入。
- [冻结计划](../../g1_retroactive_recovery/results/g1r_final_replay_20261113_v1/frozen_plan.json)：gap8的41是时间窗步数，实际候选10个；正常训练64seed、校准48seed、最终新测试100seed，正常阈值为候选最大分数95%经验分位。
- [检测计数](../../g1_retroactive_recovery/results/g1r_final_analysis_20261113_v1/detection_counts.json)：main Replay报警91/100，正确归责85/100，报警但错误归责6/100，未报警9/100；main clean报警10/100，Wilson 95%区间约[5.52%,17.44%]。

所以附件“目前补偿仍依赖已知边和事件”作为当前全项目概括**不成立**。准确的新缺口是：**已有未知事件单点Hard GLS，但没有针对多事件不确定性的集合覆盖和补偿风险机制。** 不能将旧最大事件选择重新列为新能力。

### 4.2 结果不可跨Run混用

`PROJECT`：附件Replay恢复超额0.816381、FDI超额0.000719来自旧48seed机制筛选；不是100seed最终未知归责的同一组数字。main最终Yang接收MSE 1.00771、隔离1.21465来自另一最终Run。不同已知/未知事件、窗口、seed及方法要各自标识，不拼接成一个实验表。

最终Hard选择在正常样本的10%经验报警不能作为严格5%误报保证。新风险上界中的\(\alpha\)不能直接代入0.05并声称旧部署器已满足。

## 5. 三类恢复强基线必须精确定义

### 5.1 同权限Hard GLS

`PROJECT`：原最终接口为同一full-prefix创新窗\([176,216]\)、10候选、最大分数硬归责。新方案拟用各候选自己的post-cache窗，观测数及维度不同；原阈值、分数排名和结果不能直接继承。正式比较至少需在**同一可用创新记录和相同正常校准预算**下重建Hard GLS，不通过削弱旧基线获得收益。

### 5.2 Estimated Rollback：仅改历史源包与完整修复不是一回事

`DERIVED`：固定日程、线性更新、给定候选\(h\)及估计\(\hat\theta_h\)，若从攻击前checkpoint重放本地量测，并把**每条后续实际接收记录**按已知网络响应减去相应\(S^{raw}_{k,e;h}\hat\theta_h\)，则本地重放与\(\hat x_i^a(d)-G_{i,h,d}\hat\theta_h\)逐样本相等。这是同信息线性叠加，不是新方法；不要把两个代数等价基线的差异当性能收益。

如果只修改\(r\)时刻的可疑包，却保留后续实际收到的污染载荷，那么本地反事实重放只去掉直接缓存作用；后续网络反馈造成的间接污染仍存在。它不能代表完整Estimated Rollback强基线。

完整恢复的区别来自估计量/事件选择，而不是重放与灵敏度实现形式。若只保存有限窗口，还需明确checkpoint已在攻击前，否则checkpoint本身也可能受污染。

`PROJECT`：早期[receiver_replay](../../g1_retroactive_recovery/code/minimal_recovery_screen.py)是离线从完整run对象重建真实接收输入，并使用攻击场景或`replay_source`复原已收到的历史值；它不是可原样部署的新恢复接口。正式基线应直接接收合法本地日志，不能向在线函数传scenario、replay_source或sender内部估计数组。

### 5.3 Fixed-lag Smoother

`DERIVED`：标准固定滞后平滑估计物理状态\(x\)，本方案首先恢复健康Yang反事实。二者目标不同，不能把“本地checkpoint后只用local gains重新滤波”改名为标准固定滞后平滑。旧`local_checkpoint_filter`恰是local-only重新滤波，不是RTS平滑。

如果标准平滑器能得到同一合法信息\(\mathcal I_i(d)\)下的正确条件模型，那么\(\mathbb E[x_d\mid\mathcal I_i(d)]\)对平方损失最优；新机制不能宣称无条件优于它。未知攻击分布/位置导致正确模型不可得时，必须明确双方共享的攻击先验或无先验约束，比较鲁棒性及风险，不将oracle后验或额外数据偷偷加入某一方。

目前没有保存的同权限“未知历史Replay+固定滞后+风险预算”忠实基线结果，状态为`OPEN`。不能提前声称已击败。

### 5.4 Oracle Rollback

`PROJECT/DERIVED`：真事件、真实原始载荷或真实\(\theta\)只用于离线理想参照，可恢复健康反事实；健康Yang并非真实状态MSE的逐样本或总体最优上界。建议称“反事实恢复参照”，避免无条件称“真实MSE性能上界”。

## 6. 本次有限结论

|问题|判断|
|---|---|
|已有文献是否只检测、不修正？|否。Deghat式(30)、Tabatabaei式(12)–(14)/(16)/(26)均有实质恢复|
|未知历史事件归责是否本轮首次实现？|否。项目最终Hard GLS已有未知事件最大搜索及端到端测试|
|正常情况下拒绝修正是否新想法？|否。Deghat出版社p.8已明确建议阈值切换原/修正输出|
|原文是否直接给当前方案的影响并集覆盖及正常MSE风险预算？|在上述已核查方法/定理中未发现；这只是受限排重结果，不是全领域新颖性证明|
|可以直接立项？|不能。需完成新直接竞争全文核查、构造不泄漏真标签的集合覆盖及同权限强基线验证|

最窄的可检验新增能力候选是：在**同一post-cache本地证据**下保留多个合理历史事件，将其映射为当前影响并集，再用可验证风险预算决定零/部分/全部补偿。是否超出标准集合估计与选择性决策的直接组合，仍为`OPEN`。
