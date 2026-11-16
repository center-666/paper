# G7-R0：SoD 条件下历史链路攻击事后检测的核心问题审查

日期：2026-11-16。性质：只读科研审查草稿。最终建议：**NO-GO**。

**结论先行。** 真实 SoD 会改变健康缓存残差的条件统计，但不能概括为“所有残差都不再高斯”，也不能由此判定原 G1 的经验阈值已经失效。原 G1 已用完整经验协方差、缓存周期最大值和正常数据标定，明确没有宣称精确独立高斯或全时段严格5%保证。尚未解决的是其固定日程、带裁剪/隔离反馈的试验资产向“真实 SoD＋原 Yang 不变”的迁移；这不是本轮首次发现的错误卡方检测器。

本轮给出了与实际代码一致的选择分布推导、首个 SoD 时刻的确定性数值核验及有限样本标定边界。所得条件统计和修正工具已有直接文献或标准统计方法支持，尚没有证据表明其比“保持原评分，在真实健康 SoD 下正确重新标定”多出有意义的决策价值。因此不建议据此直接立项普通中文学报论文；不启动完整检测器或实验。

标记：**FACT**＝代码/既有报告/论文直接支持；**DERIVED**＝明确假设下推导或确定性计算；**HYPOTHESIS**＝未验证假设；**OPEN**＝当前证据缺口。NO-GO是本轮建议，研究决策由负责人作出。

## 1. 基线、继承范围及权限

**FACT。** 工作位置为隔离仓库 C:/Users/zhongxin/shixidoc/mypaper_g1r_e2_status_contract，分支 g1r-e2-status-contract-20261115，HEAD：

    03a00789508755f1df9bf16dee901af37d7e34f1

本地与只读远程查询一致；父提交9debe50360dc80bca0b3228351da65dc53709a0a包含正式E3。开始时存在G1-R 27/28及G6-R0未跟踪草稿，均保留。用户先前要求成果上传GitHub，但本次G7-R0任务书随后明确禁止commit/push，本轮按最新具体限制执行，仅新增本报告。G6-R1分析不作为本报告已完成成果，不继续其延迟鉴别方向。

### 1.1 继承清单

| 内容 | 本轮核查入口 | 使用边界 |
|---|---|---|
| 原始缓存检测 | [cache_monitor.py](../../simulation/cache_monitor.py)、[cache_screen.py](../../simulation/cache_screen.py)、[cache_aged_confirmation.py](../../simulation/cache_aged_confirmation.py) | 已有instant/joint/动态模板GLS/mean及episode最大值；不能再说动态HA模板尚未实现 |
| 分阶段序贯检测 | [sequential_cache.py](../../simulation/sequential_cache.py)、[run_sequential_validation.py](../../simulation/run_sequential_validation.py)、[sequential_validation_plan.json](../../simulation/sequential_validation_plan.json) | 完整prefix协方差、白化窗口、CUSUM、分阶段阈值、正常调参 |
| 跨包与压力验证 | [run_carry_cusum_audit.py](../../simulation/run_carry_cusum_audit.py)、[run_partial_observability_probe.py](../../simulation/run_partial_observability_probe.py) | 旧对照、负结果保留，不复跑 |
| G1既有统计审计 | [identifiability_audit.md](../fdi_replay_20261112/identifiability_audit.md)、[g1_existing_code_audit.json](../fdi_replay_20261112/g1_existing_code_audit.json)、[g1_decision.md](../fdi_replay_20261112/g1_decision.md)、[g1_experiment_plan.md](../fdi_replay_20261112/g1_experiment_plan.md) | 已指出SoD选择与survival条件、共享缓存误差、信息饱和 |
| G1结果报告 | reviews/fdi_replay_20261112/evidence/prior_results/下sequential_strong、cusum_carry、partial_observability报告 | 实际固定gap8/irregular日程，不是闭环SoD结果 |
| Yang与缓存核心 | [engine.py](../../simulation/engine.py)、[model.py](../../simulation/model.py)、[config.json](../../simulation/config.json)、[reference_exploration_plan.json](../../simulation/reference_exploration_plan.json) | 原估计器不改；区分默认与异质感知模型 |
| G1-R传播与定位 | [07_full_horizon_propagation_audit.md](../g1_retroactive_recovery/07_full_horizon_propagation_audit.md)、code/p0_verified.py、code/receiver_gls_writeback.py | 已有完整污染传播及未知接收事件搜索，不重写 |
| G1-R联合统计/风险/冻结 | [07_replay_joint_probability_model.md](../g1r_risk_constrained_recovery/07_replay_joint_probability_model.md)、02数学审计、06/10协议、11/12求解权限公平性报告 | 固定外生日程的Gaussian矩阵不能直接充当SoD条件矩阵 |
| E2/E3 | [21号E2报告](../g1r_risk_constrained_recovery/21_e2_final_report_20261116.md)、[22号覆盖复核](../g1r_risk_constrained_recovery/22_e2_independent_coverage_audit.md)、[26号E3报告](../g1r_risk_constrained_recovery/26_e3_formal_experiment_report.md) | E2 PASS；E3完整完成但NO_GO_PERFORMANCE；不作本轮检测结论 |
| B0、后续诊断 | [28号B0](../g1r_risk_constrained_recovery/28_B0_identifiability_and_recovery_bound_audit.md)、27号成果/诊断报告 | 恢复不可辨识与检测虚警不是一个终点 |
| G6-R0 | [01_research_direction_audit.md](../g6_retrospective_detection/01_research_direction_audit.md) | 继承时序与文献；本轮收窄，不加入正常延迟/丢包模型 |

**FACT。** 旧E3主场景MSE为Yang 9.8996305110、Hard 9.6568284428、Soft 9.6542652447、Set 9.6618472242；Set相对Yang改善2.40194%，但两项最坏事件优势未通过。E2的集合覆盖及补偿非零率均不能当作历史攻击检测率或SoD虚警保证。B0为未具备独立理论立项资格的审查结论，不证明本轮统计问题没有意义。

**FACT。** 本轮不调用任何generate_data、simulate或E2/E3运行入口；只读取NPZ中的既有矩阵并进行Gaussian积分和线性代数。下文代码块为复核说明，未新增可执行检测器。

## 2. 问题1：真实SoD及缓存机制逐项核查

### 2.1 准确时间索引与更新

**FACT，engine.py约第53—76、153—173行，model.py nominal_gains。**

\[
x_{k+1}=Ax_k+w_k,\qquad y_i(k)=H_ix_k+v_i(k).
\tag{1}
\]

\(\hat x_i(k)\)为使用\(y_i(k)\)之前的预测估计。先计算
\(\nu_i(k)=y_i(k)-H_i\hat x_i(k)\)，再形成

\[
\hat x_i(k+1)=A\hat x_i(k)+K_i(k)\nu_i(k)
+\epsilon A\sum_{j\in N_i}\big[\bar q_{ji}(k)-\hat x_i(k)\big].
\tag{2}
\]

缓存外推是\(\bar q_{ji}(k)=A^{a_{ji}(k)}q_{ji}\)，其中年龄为距最后**接收**时刻的差。method=yang时不裁剪、融合权重为1。本轮所有理论针对这个固定更新，报警不得返回改变融合的权重。

**FACT。** model.py声明是Yang-form研究实现、不是原论文完整复现；nominal_gains按q=1、全链路即时通信的联合协方差求增益。Yang2014原文PDF第2页式(2)—(5)采用Bernoulli激活而非当前SoD缓存协议，原最优性/稳定性定理不能无条件移植。原PDF：Zotero/4YP6FLZG。本轮不修改该既有实现。

### 2.2 代码与规则对照

| 核查项 | 实际实现 | 结论 |
|---|---|---|
| 比较对象 | hat与last_send_value | 比较当前预测估计和最近一次实际发送时的估计；不是当前innovation、量测或上次接收缓存 |
| 触发条件 | sum((hat-last_send_value)**2)>send_delta_squared | 平方欧氏范数严格大于阈值 |
| 触发阈值 | simulation/config.json：0.12 | 范数阈值为sqrt(0.12)≈0.346410；不能把0.12当范数阈值 |
| 额外定时发送 | k-last_send_time>=max_interval；max_interval=10 | 到时强制发送，不要求幅值跨阈 |
| 初始化 | k=0强制所有节点发送 | 初始发送不提供跨阈选择信息 |
| 参考更新 | 发送时last_send_value←hat、last_send_time←k | 在攻击替换incoming之前更新；发送端记的是真实发送估计 |
| 未发送时 | payload和last_receive保持 | raw载荷不变；用于融合的A^age载荷随年龄演化 |
| 新包时 | 先覆盖payload、last_receive=k，再算age/aligned | 本拍age0；第一次影响估计是k+1 |
| 过期清理 | 无 | 缓存不按年龄删除；健康下由timeout保证刷新 |
| 发送/接收 | fresh=transmit[:,src] | 当前仿真为即时可靠到达；没有独立丢包、延迟、重排机制 |
| 外部schedule | schedule非None时直接取其布尔值 | 覆盖SoD，配置文件仍写0.12并不代表该次运行使用SoD |
| 丢包后的两端一致性 | 当前未实现丢包 | 不能声称已有丢包后的同步保证；若将来增添丢包，发送参考与接收缓存可能不同，须另建协议 |
| 检测缓存长度 | SequentialController中age>=max_interval报错 | 是检测器数值边界，不是engine自动清空过期缓存 |

**DERIVED。** 令\(m_j^{last}\)、\(\ell_j\)是上次发送值与时刻，则非初始化时：

\[
S_j(k)=1\{\|\hat x_j(k)-m_j^{last}\|^2>0.12\}
\lor1\{k-\ell_j\ge10\}.
\tag{3}
\]

虽然代码先算本拍innovation再判断发送，式(3)并不使用它；它只通过\(\hat x_j(k)\)依赖以前的量测。这个因果顺序是后文分布推导的关键。

### 2.3 唯一攻击与在线权限

**FACT / 研究范围。** 只考虑在一个真实发送机会\((j,r)\)将正常载荷替换为已经截获、确实发送过的旧载荷：
\[
q^a_{ji}(r)=\hat x_j(s),\quad s<r,\quad S_j(s)=1.
\tag{4}
\]
攻击者可保存目标链路历史、在允许的发送机会选择旧载荷；本轮不赋予其丢包、额外发送、改时序或改传感器量测的能力。当前机会的SoD判决已经形成，替换不会反向改变它；之后估计被污染，未来SoD可能改变。研究的是此前未立即报警后的事后验证，不添加新的即时拦截策略。

检测器只读本地量测/创新、实际接收载荷/时刻、缓存与年龄及公开模型。不得输入真实源时刻s、攻击标签、真状态、未发送邻居状态或健康反事实。正常即时通信下某条入边的发送/静默可由fresh推知；全网其他边的触发历史不能因此变成该节点合法信息。

## 3. 问题2与4：原G1究竟用了什么统计量和阈值

### 3.1 原始残差与两套既有实现

**FACT。** G1缓存episode残差为
\[
r_{\tau+a}=y_i(\tau+a)-H_iA^a q_{ji}(\tau),\quad a=0,\ldots,L-1.
\tag{5}
\]
它不同于本地innovation \(y_i-H_i\hat x_i\)。下一新包到达时先结束旧episode，再给新包记age0；旧episode不包含该新包时刻的残差。

**FACT。** 当前cache_monitor.py的CacheMonitor.fit已经构造
\[
M_L=\operatorname{col}(H_i,H_iA,\ldots,H_iA^{L-1})
\]
并用白化后的M_L做SVD投影，得到动态模板GLS；同时有联合能量、瞬时分数及平均分数。不能只看后来的sequential_cache.py就说项目没有动态GLS。本轮不修改G6-R0历史报告，在此补充准确实现范围。

**FACT。** sequential_cache.py的分阶段mean为
\[
T_L=d_L^TC_L^T(C_L\widehat\Sigma_LC_L^T)^{-1}C_Ld_L,\quad
C_L=[I,\ldots,I]/L,\quad d_L=r_{\tau:\tau+L-1}-\widehat\mu_L.
\tag{6}
\]
这不是所有动态模板GLS的同义改写。其白化量是
\[
z_L=[\operatorname{chol}(\widehat\Sigma_L)^{-1}]_{\text{末块}}d_L.
\]
还实现窗口能量和
\(C_L^{energy}=\max(0,C_{L-1}^{energy}+\|z_L\|^2-m)\)，以及双侧分量CUSUM。跨包版本保留CUSUM，报警后重置；缓存隔离保持到新包。

### 3.2 协方差、条件化程度和阈值

**FACT，PhaseStatistics.fit。**

- 先保留complete=True的训练/校准episode。
- 按起始phase（初始/过渡/稳态）、edge、当前prefix长度分组。
- 长度L的矩估计只用完整episode中长度至少L的prefix；样本足够时是全联合协方差，样本不足时采用逐年龄块对角fallback，并加ridge。
- 用每个校准episode所有prefix分数的最大值，取np.quantile(...,.95,method="higher")为基础阈值。
- 运行器还在独立tune轨迹上四轮重标multipliers，再用normal_audit和test报告经验误隔离率。

**DERIVED。** 它既非“完全不考虑事件”，也非“精确按整个SoD历史条件化”：edge/phase/当前年龄及episode存活长度筛选已保留部分条件信息，但没有计算完整触发历史的截断概率。complete筛选还涉及未来是否在有限观察期内关闭episode；不能把这种训练样本筛选等同于在线可见条件。

**FACT。** sequential_cache.py开头明确声明经验矩在selection/feedback下是近似，不宣称精确Gaussian或独立增量。计划文件distribution_warning及旧结果报告也明确说阈值不是独立卡方公式。

| 可能的假设 | 对原G1的准确判断 |
|---|---|
| 跨时间残差独立Gaussian | 未作为最终阈值保证假设；full covariance本就保留相关 |
| 联合Gaussian | 可用作矩白化解释，但实现明确是近似，不提供精确后验密度 |
| 阈值取χ²分位数 | 否；采用正常episode最大值经验分位数及调参 |
| 固定协方差 | 拟合后冻结；按phase/edge/长度有多套矩，不是一个全局Σ |
| 与通信事件无关 | 否；残差定义、年龄、prefix存活及校准日程均有关；但没有精确SoD选择律 |
| 白化后独立 | 不保证；不同L分别估计且条件样本集不同，矩块未必构成同一个联合分布的一致边缘 |
| 所有时刻P_FA≤5% | 原报告未作该严格主张 |

### 3.3 旧实验的两个迁移障碍

**FACT。** run_sequential_validation.py通过get_schedule生成gap8/irregular外生日程；不是schedule=None的闭环SoD。run_study.py另有SoD通路及早期触发一致性探针，不能据此说整个项目从未运行SoD；但它们不是这个序贯缓存方案的精确条件阈值验收。

**FACT。** 更重要的是，原序贯训练用age_only控制器＋capped更新；正式对照也用capped及检测反馈。SequentialController.update返回
\[
w_{ji}(k)=1_{\{\text{未被隔离}\}}\,2^{-a/half\_life}.
\]
它会改估计器融合，与本任务“原Yang不改、仅旁路检测”不同。原矩/阈值不能直接拿来声称已覆盖G7健康模型。即使外生日程固定，裁剪和报警反馈也使整体映射非线性。

**FACT。** 旧sequential strong报告明确保留normal-audit/test经验值；例如gap8 mean稳态测试约5.262%，irregular约5.343%。这些是有限样本经验值，不是证明总体虚警严格超标的证据，更不是SoD选择效应的测量。完整性能门槛仍为1/4；跨包补充3/4不撤销主负结果。

**结论。** 原G1没有建立真实SoD的精确条件统计；但“G1错把独立卡方当健康阈值”的前提不成立。

## 4. 命题1：健康SoD条件残差分布

### 4.1 健康假设及原始Gaussian变量

**DERIVED，适用假设。** H0为式(1)—(3)、原Yang更新、无攻击、即时可靠通信、零初始估计/缓存；初态及各时刻/节点的过程与量测噪声按model.generate_data的独立Gaussian假设。只读地把截至有限时刻t的原始噪声标准化堆叠为
\[
\xi\sim N(0,I).
\]
这只是分布变量，不抽样、不生成轨迹。固定K、A、H、阈值、timeout；不启用capped/age权重/隔离。

令\(\sigma=\{S_j(k):0\le k\le t,\forall j\}\)是一个全网发送模式。先将该模式作为外生开关代入**现有**状态/缓存递推。由于式(2)线性，且last_send值/缓存来源在给定模式下确定，所有估计、缓存、触发差以及长度L的目标残差均为ξ的线性函数：
\[
\hat x_j(k)-m_j^{last}=D_{j,k}^{\sigma}\xi,\qquad
R_L=B_{\sigma,L}\xi.
\tag{7}
\]
不是重新开发传播器；这是既有线性传播在固定模式内的数学表达。

### 4.2 精确模式区域

对非初始化且尚未timeout的时刻，
\[
\begin{cases}
\|D_{j,k}^{\sigma}\xi\|^2\le\delta,&\sigma_j(k)=0,\\
\|D_{j,k}^{\sigma}\xi\|^2>\delta,&\sigma_j(k)=1,
\end{cases}\quad \delta=0.12.
\tag{8}
\]
timeout或k=0必须发送，否则该模式不可行；**timeout发送不能额外施加跨阈约束**。令全部条件交集为\(\mathcal C_\sigma\)，其概率为\(Z_\sigma=P(\xi\in\mathcal C_\sigma)\)。

对\(Z_\sigma>0\)，精确条件律是
\[
P(R_L\in E\mid\sigma)=
\frac{\int 1_{\mathcal C_\sigma}(\xi)\,
1_E(B_{\sigma,L}\xi)\,\varphi(\xi)d\xi}{Z_\sigma}.
\tag{9}
\]

**证明。** 给定模式下所有更新线性，式(7)逐拍成立；该线性分支是真实SoD轨迹的充要条件就是所有触发/非触发/timeout条件一致，即ξ属于\(\mathcal C_\sigma\)。在该事件上应用条件概率定义即得式(9)。不需要假设残差独立，不需要攻击真值，也不需要读未来量测。

**分类。**

- 原始ξ条件于模式，是在若干二次不等式交集上截断的Gaussian；区域可非凸。
- 残差是该截断Gaussian的线性像，一般是**选择分布**；不必是对残差坐标直接截断的Gaussian，也不必属于普通有限Gaussian混合。
- 若只观察局部发送史s，应对其兼容的隐藏模式求和：
\[
P(R_L\in E\mid s)=
\sum_{\sigma:\sigma|_{\rm local}=s}
P(\sigma\mid s)\,P(R_L\in E\mid\sigma).
\tag{10}
\]
是选择分布的混合；不能把全网模式作为接收端输入。
- 若条件于收到的具体载荷、本地已观测数值，还须在式(9)中加入相应线性观测条件，再对隐藏模式积分。给定这些具体值后的Gaussian条件先验，仍可能被剩余触发条件截断。
- 外生固定模式不包含选择事件时，式(9)退化为普通Gaussian线性像；某些独立性结构下，即使有选择，目标残差也可能保持Gaussian。

**DERIVED。** 若固定分支目标R具有密度，则亦可写
\[
p(R=r\mid\sigma)=p_{\sigma}^{lin}(r)
\frac{P(\xi\in\mathcal C_\sigma\mid B_{\sigma,L}\xi=r)}
{P(\xi\in\mathcal C_\sigma)}.
\tag{11}
\]
条件密度等于外生分支Gaussian密度的必要充分条件，是右侧选择权重对r几乎处处恒定。触发量与R联合Gaussian且独立是充分条件，但不是一般自动成立的条件。

### 4.3 不发送、共享缓存及prefix存活

**DERIVED / 继承G1恒等式。** 健康包在τ发送，\(e_j(\tau)=x_\tau-\hat x_j(\tau)\)，同一episode：
\[
r_{\tau+a}=H_iA^ae_j(\tau)+
\sum_{s=0}^{a-1}H_iA^{a-1-s}w_{\tau+s}+v_i(\tau+a).
\tag{12}
\]
若没有触发选择，且e_j与未来噪声独立，其协方差含共享误差项和共同过程噪声项：
\[
\Sigma_{ab}=H_iA^aP_e(A^b)^TH_i^T+
\sum_{s=0}^{\min(a,b)-1}H_iA^{a-1-s}Q(A^{b-1-s})^TH_i^T
+1_{\{a=b\}}R_i.
\tag{13}
\]
这是G1已有结果，不是G7新定理。

实际prefix活到τ+a还意味着\(S_j(\tau+1)=\cdots=S_j(\tau+a)=0\)，这些不等式会选择e_j和其后的过程/量测噪声。条件化后不能继续用原无条件P_e、Q和全部零交叉项写成式(13)。对于本地innovation还须保留网络估计反馈协方差。

**DERIVED。** 接收端的“当前未到达”在本轮可靠即时通信下就是该入边发送端未触发；不需要混入正常丢包。但只能推知该发送端状态，不得偷读全网S。观察结束时未闭合episode是右删失，丢弃它会改变目标抽样分布。

### 4.4 零均值不等于Gaussian；发送标志也可能冗余

**DERIVED。** 在零均值原始噪声、零初始估计及平方范数触发下，\(\xi\mapsto-\xi\)保留全网模式，R变号，所以仅条件于模式时条件均值仍为零（可积时）。这并不保证条件协方差或尾概率不变。给定非零具体载荷/过去量测后，该对称性一般不再成立。

当当前及上次真实发送载荷已被接收，且本次不是timeout，健康条件下“发送”可由这两个载荷的差重构。再次把同一发送事件当成一个独立似然因子会重复计数。未发送时恰好缺少当前载荷，非发送不等式才是新增的区间信息。完整联合信息集必须一次性处理。

## 5. 与实际矩阵一致的确定性核验：既有选择效应，也有精确例外

本节只使用07号已存NPZ的A、H和k=0增益。采用G1异质感知模型，不把它与默认同质H混为一个配置。NPZ中第一拍增益不受之后外生日程影响：所有估计初始化为0，k=0都发送且载荷0，因此与实际健康SoD的第一拍完全相同。

**FACT。**
\[
A=\begin{bmatrix}1&.1\\0&1.01\end{bmatrix},
\quad H_0=\operatorname{diag}(1,.15),\quad
H_1=\operatorname{diag}(.15,1),\quad P_0=I,\ Q=.02I,\ R_i=.05I,
\]
\[
K_0(0)=
\begin{bmatrix}
.952380952381&.206896551724\\0&2.089655172414
\end{bmatrix}.
\]

### 5.1 k=1的真实两分支

令\(X=\hat x_0(1)=K_0(0)y_0(0)\)、\(Y=y_1(1)\)。上次发送估计为0，k=1尚不timeout，所以
\[
S_0(1)=1\{\|X\|^2>.12\}.
\]
接收端原始G1残差为
\[
R_{\rm send}=Y-H_1X,\quad
R_{\rm hold}=Y
\]
分别对应新包覆盖和继续保持k=0的零缓存。

**DERIVED。** X、Y联合Gaussian，记V_X、V_Y、C_YX：
\[
V_X=K_0(H_0P_0H_0^T+R_0)K_0^T,
\quad V_Y=H_1(AP_0A^T+Q)H_1^T+R_1,
\quad C_{YX}=H_1AP_0H_0^TK_0^T.
\tag{14}
\]
对分支R=Y−BX，令\(F=(C_{YX}-BV_X)V_X^{-1}\)，则
\[
\operatorname{Cov}(R\mid E)=
V_R-FV_XF^T+F\operatorname{Cov}(X\mid E)F^T,
\tag{15}
\]
其中E为球内或球外事件；对称性使本例均值为0。

本例\(K_0(0)=AP_0H_0^T(H_0P_0H_0^T+R_0)^{-1}\)，因而\(C_{YX}=H_1V_X\)。所以
\[
\operatorname{Cov}(R_{\rm send},X)=0.
\]
联合Gaussian下二者独立，故**新发送包残差在该首步条件于发送仍精确Gaussian**。这并不推广为所有后续时刻都独立。

### 5.2 积分结果

**DERIVED。** 用二维Gaussian在半径sqrt(.12)球内的概率和二阶矩积分，得到：

| 指标 | 结果 |
|---|---:|
| P(保持缓存) | 0.102671675658707 |
| P(发送) | 0.897328324341293 |
| hold分支条件/无条件协方差迹之比 | 0.734671745670272 |
| send分支条件/无条件协方差迹之比 | 1.000000000000000 |
| send残差与触发量交叉协方差最大数值绝对值 | 5.56×10^-17 |

\[
V_Y=
\begin{bmatrix}.073175&.01515\\.01515&1.0901\end{bmatrix},\qquad
\operatorname{Cov}(Y\mid S=0)=
\begin{bmatrix}
.052351331738&.010457337322\\
.010457337322&.802273943207
\end{bmatrix}.
\tag{16}
\]

因此保持事件令协方差迹下降约26.53%。这是首步解析分布，不是稳态经验估计或“正常风险改善”。

**DERIVED。** 若对hold分支第一残差分量错误沿用其未条件化Gaussian的双侧5%阈值，其实际条件超阈概率为
\[
P\{|Y_1|>1.95996398454\sqrt{.073175}\mid S=0\}
=0.020490151651765.
\tag{17}
\]
两套积分容差10^-9、10^-11结果一致；外层概率积分误差估计约10^-14，尾概率积分约10^-17。这是数值积分一致性检查，不是区间算术证明。

**解释边界。** 本例证明条件统计确实改变，也证明变化可能使阈值更保守，而非必然虚警膨胀。式(17)是单分量Gaussian参考阈值，**不是原G1最终episode最大值门限的实际FPR**。不能把2.049%贴成旧实验误报率。

## 6. 命题2：原阈值是否满足P_FA≤α

### 6.1 先固定概率单位

**DERIVED。** 以下四种保证不同：

1. 固定时刻边际虚警 \(P_0(T_k>q)\)；
2. 给定某个可见事件史的条件虚警 \(P_0(T_k>q\mid s)\)；
3. 一个按预定抽样规则选出的缓存episode至少报警一次；
4. 一条预定长度轨迹上所有边、所有episode至少报警一次。

原G1校准/报告主要针对完整episode，并按phase报告；不是第4项，更不是对所有s成立的第2项。后续若改变指标，必须明说，不得据不同分母制造旧方法失败。

### 6.2 Gaussian阈值的条件反例成立，但不是原代码阈值

**DERIVED / STANDARD。** 取\((X,R)\)标准二元Gaussian，相关系数ρ=.8，触发\(S=1\{|X|>1\}\)。对\(T=R^2\)使用χ²_1的95%分位数3.841458820694，确定性积分得到：
\[
P(T>q\mid S=1)=.143314375649264,\quad
P(T>q\mid S=0)=.006627965906596,
\]
而总边际\(P(T>q)=.05\)。证明式：
\[
p(r\mid S=1)=\varphi(r)\frac{P(|X|>1\mid R=r)}{P(|X|>1)}.
\tag{18}
\]
从条件Gaussian积分即得上值。

它说明“边际5%”不能直接解释为“发送条件下5%”。该例使用与SoD相同的阈值选择结构，但不是完整五节点Yang的模拟，也不是原G1实际超标证明。精确Gaussian白化若忽略条件选择，不能保证条件χ²尾界；相关不等于一定失效，见第5节send独立例外。

### 6.3 正确的经验分位数不需要Gaussian

**DERIVED / STANDARD。** 设评分及抽样单位已冻结，M为真实健康SoD下该单位内最大分数，F为其真实CDF。取q满足F(q)≥1−α，严格M>q报警，即有
\[
P_0(M>q)\le\alpha
\tag{19}
\]
而不需要Gaussian、独立时刻或精确协方差。因此SoD非Gaussian**本身不否定**episode最大值标定。

但(19)是总体分位数命题；有限校准样本需满足交换性及正确顺序统计量。n个独立/交换校准分数加一个同律测试分数，固定评分且无并列时，对第k个顺序统计量
\[
P(M_{new}>M_{(k)})=\frac{n+1-k}{n+1}.
\tag{20}
\]
有并列且严格大于时是保守上界。

### 6.4 原实现的有限样本与依赖边界

**DERIVED。** np.quantile(x,.95,method="higher")使用的1基秩为
\(k_{old}=1+\lceil.95(n-1)\rceil\)，不总等于严格5%边际保证所需的\(\lceil.95(n+1)\rceil\)。

| 假设独立连续分数数量n | 原秩 | 式(20)超阈概率 | 保证≤.05所需秩 |
|---:|---:|---:|---:|
| 96 | 92 | 0.05154639 | 93 |
| 4032 | 3831 | 0.05008678 | 3832 |
| 864 | 821 | 0.05086705 | 822 |
| 8160 | 7753 | 0.04999387 | 7753 |

**限制。** n=96可对应原初始phase每条边一episode/Seed的基础校准；其后还有tune和反馈，因此上述数值不是最终门限的FPR。4032等是已有分组计数，但包含同Seed相关episode，不满足表内独立秩假设，不能据此为它们作精确保证。该表只证明“higher分位数自动给严格5%”不是通用定理。

同一轨迹的episode不一般交换；将独立Seed拆成许多episode不会获得相应独立标定样本数。极端例子是n个分数都等于同一个连续随机变量U，独立新分数V同律：阈值仍为U，\(P(V>U)=1/2\)。这不是本项目实际相关强度，只反驳无需依赖假设的分位数保证。

**FACT。** 四轮tune复用同一tune集且评分受隔离反馈影响；最后独立audit/test合理地报告了经验值，但不等于附带严格有限样本概率证书。旧报告对此有明确限制，并没有需要撤回的“全时段严格5%”主张。

### 6.5 日程与估计器迁移

**DERIVED。** 旧门限q_old在旧分布F_old的校准不能保证在真实SoD、无干预Yang的新分布F_sod有效。准确失效条件是
\(F_{sod}(q_{old})<1-\alpha\)；若有分布总变差界ε，则最多只能继承
\[
P_{sod}(M>q_{old})\le P_{old}(M>q_{old})+\epsilon.
\tag{21}
\]
本项目尚未计算该完整评分分布距离；不因为理论上可失效就称现有系统已经实测超标。裁剪/age衰减/隔离、SoD/外生日程、删失及抽样权重都需一致。

**命题2判定。**

- **不成立：** “原经验代码在任意新SoD、任意事件条件或全轨迹下自动严格控制5%”。
- **未被否定：** “在目标健康分布上独立正确校准的固定评分可控制其约定的边际虚警”。
- **OPEN：** 原冻结G1具体门限迁移到被动原Yang＋真实SoD后的实际虚警数值。本轮没有这样的独立数据，且禁止生成数据。
- **FACT：** 旧报告的有限经验结果和其限定陈述无需因本轮推导作废。

## 7. 命题3是否必要：仅为明确的保证缺口给最小修正

**DERIVED。** 若只忠实报告旧固定日程实验，没有必要为了“Gaussian被破坏”另造检测器。若希望声称G7健康模型下严格P_FA保证，则必须补正确的目标分布/样本单位校准；原因是第6节的迁移与有限样本缺口，而非所有SoD残差都错误。

### 7.1 最小保守方案：保持评分、独立轨迹最大值标定

仅作为可证明的标准设计说明，不实现、不校准。

- 保留已有mean或GLS评分公式；训练与门限校准严格分开。
- 固定监测边/时间范围和评分，旁路读取原Yang＋真实SoD；不使用旧隔离controller的返回权重。
- 每个独立健康轨迹形成一个最大分数M，包含事先约定的全部报警机会及观察期末的有效prefix。
- n个校准轨迹取\(k=\lceil(n+1)(1-\alpha)\rceil\)，若k>n则阈值为+\(\infty\)；严格过阈报警。

**DERIVED / STANDARD。** 条件于独立训练结果，交换的校准和新轨迹最大分数按秩给
\(P(\text{新轨迹至少一次误报})\le\alpha\)。不需要时刻独立或Gaussian。这是对校准集和新轨迹共同随机化的边际保证，不是对每份已实现校准集的条件保证，也不保证每个SoD史的误报都≤α。

不把这个更严格的全轨迹预算与旧每episode预算直接比较检测率。若只要episode预算，须先规定不依赖其未来分数的独立episode抽样规则，再按相同单位比较。此方案是标准秩标定，不是新算法贡献。

### 7.2 只有明确需要条件公平性时才考虑条件阈值

若研究要求给某个预定、在线可见条件G（例如当前接收年龄/非timeout的新包标志）单独控制风险，可定义
\[
q_G=F^{-1}_{M\mid G}(1-\alpha_G).
\tag{22}
\]
需要真实的条件分布或独立同条件标定单位。不能把未来总episode长度、隐藏全网触发模式或真实Replay源用作G；频繁稀疏分组可能导致阈值不可用。连续完整历史逐点条件保证不由简单分组经验分位数自动得到。

命题1给出了精确但维度增长的积分表达；本轮没有证明完整条件化比同风险边际标定更有检测能力，因此不将其作为必须开发的新算法。有限条件分组与条件分布建模也有既有统计先例。

### 7.3 历史替换下的功效边界

**DERIVED。** 外生日程固定时已有\(z=\eta+O_h\theta\)，但真实SoD下历史替换会改变未来模式，不能把原固定O、固定健康Σ直接用于非中心χ²功效结论。旧数据构造的θ与η相关，亦不能默认独立。精确功效只能写为允许攻击策略下
\[
P_a\{\text{已有评分越过已冻结健康阈值}\}
\]
并按真实模式变化计算；本轮未得到该概率的非平凡统一下界。

**OPEN。** 保证健康虚警不等于保留非零检出能力。不能通过只校准正常数据就宣称对任意历史替换有优势，也不能用E2覆盖率/E3补偿触发率替代验证。

## 8. 直接竞争文献：公式、假设与贡献边界

优先使用已下载全文。新增定向记录不超过6篇：Han2015、He2019、Chitraganti2018、Qiu2024共4篇；其他仅搜索命中而未纳入证据。没有开展大范围FDI/Replay查新。

### 8.1 已取得公式级证据

| 文献 | 具体模型/公式/保证 | 对G7的约束 |
|---|---|---|
| Qian等2023，TAC，Event-Triggered Distributed State Estimation: A Conditional Expectation Method；Zotero I73VQTUU，PDF2—4页 | 式(3)按当前innovation无穷范数决定发送，式(4)改变估计更新；Assumption2/Remark3明确采用Gaussian近似；Lemma1给非发送截断二阶矩；Theorem1等在其假设下分析 | 非发送信息改变条件矩不是新发现。其trigger及估计器不同，不能照搬为本项目精确统计；尤其不能把其近似叫成精确Gaussian |
| Qiu等2019，TIE，A Tradeoff Approach for Optimal Event-Triggered Fault Detection；Zotero ZTYZTNYQ，PDF2—5页及§III-B | 式(2)(3)相对量测触发/ZOH误差；式(6)(7)残差显式包含触发传输误差；Theorem3.2设计H∞/H∞残差，后续阈值考虑扰动和触发误差 | “触发会影响残差，阈值应修正”已有。其有界能量/稳定闭环保证不等于本项目Gaussian概率虚警 |
| Liang–Liu2023，TIM；Zotero QXDIH3U9，PDF4—6页 | 式(18)邻居残差含trigger误差；式(28)—(30)以该误差给阈值；UIO存在与隔离条件 | 已有事件通信下攻击检测和阈值；物理耦合MAS/邻居量测不同于共享状态Yang估计缓存 |
| Han等2015，TAC，DOI10.1109/TAC.2015.2406975；作者稿arXiv1402.0599，PDF3—4页 | 式(11)—(13)用随机阈值及指数二次不发送概率；Theorem1和式(26)—(42)证明Gaussian保持及精确MMSE递推 | 明确指出确定性触发一般破坏Gaussian；解决办法需改变发送机制。本轮不能换成随机触发后称原SoD已解决 |
| Tunga等2018，Tuning Windowed Chi-Squared Detectors for Sensor Attacks；Zotero F5CLVDL6，PDF2—4页 | 式(13)(14)窗口残差能量；Theorem1阈值证明使用独立χ²和 | 不能直接套到相关缓存残差；但原G1本来就没把它作为最终门限公式 |

**FACT。** Han作者稿通过贝叶斯更新将Gaussian密度乘上指数二次非发送概率，因而仍可Gaussian闭合；而本项目式(8)乘的是硬指示函数。两者不是相同分布。Han的结果支持本轮分类，却不提供不改SoD的现成闭式滤波器。

**OPEN。** Chitraganti2018已由作者主页及出版元数据确认是事件触发GLRT的直接竞争候选；其全文下载返回403，Elsevier接口仅返回短元数据。本轮不将未获得的正文公式、故障幅度假设或阈值定理当作已核实证据。

### 8.2 缺全文或只完成部分核查的记录

| 文献 | 已核实 | 未核实与影响 |
|---|---|---|
| He、Chen、Qi，Event-Based State Estimation: Optimal Algorithm With Generalized Closed Skew Normal Distribution，TAC64(1):321–328，2019，DOI10.1109/TAC.2018.2829121 | 正式元数据、作者摘要及Qian2023 Remark3直接引述其GCSN结果 | 本轮未取得可逐式核查全文，不能断言本项目欧氏球、timeout、全网缓存恰落入其闭式族，也不能以缺全文宣布新颖 |
| Qiu、Hu、Wu，Event-Triggered Fault Detection — An Integrated Design Approach Directly Toward Fault Diagnosis Performance，JAS，2024年12月，DOI10.1109/JAS.2023.124074 | 出版者/注册元数据，主题涉及面向检测性能的事件设计 | 全文访问未成功；不虚构其定理、虚警公式或与G7的完整包含关系 |
| Chitraganti、Sid、Aberkane2018，Event triggered fault detection in linear systems using Generalized likelihood ratio test，IFAC-PapersOnLine51(1):444–449，DOI10.1016/j.ifacol.2018.05.073 | 作者主页列出正式论文及其PDF入口，注册元数据一致 | PDF入口返回403，未完成模型、具体公式和定理核查；不能仅据题名判定其覆盖G7或遗漏阈值问题 |

以上缺口阻止“已完成所有竞争排重”的主张，但不妨碍根据已读原G1、Han、Qian、Qiu2019和Liang–Liu，否定把条件化或事件相关阈值本身当作新方法。

**文献出处。** Zotero根目录为C:/Users/zhongxin/Zotero/storage。新增全文只在内存读取，没有写入仓库：

~~~text
Han作者稿：https://arxiv.org/pdf/1402.0599
作者稿SHA256：bed1307e7358d1b6e9fb94c450e37388aacc6fb9c8365db20524881212ae4cea
Chitraganti作者主页：https://shaikshavali-chitraganti.github.io/publications
作者主页所链全文：https://www.researchgate.net/publication/325829184_Event_triggered_fault_detection_in_linear_systems_using_Generalized_likelihood_ratio_test
~~~

Chitraganti入口仅作为后续全文定位，不冒充已读正文。上述He、Qiu正式年份按出版元数据记录，不把DOI中的2018/2023自动当卷期年份。

## 9. 如果负责人仍要求继续：最小设计及停止门槛

本节是决策材料，不是新预注册、开发或实验授权。

**DERIVED / 建议。** 最小路径应首先保持原G1评分，而不是新增复杂滤波器：

1. 明确评价为固定观察域全轨迹虚警，或预先定义的episode虚警，两者选一。
2. 用原Yang＋真实SoD产生的合法记录作被动评分；暂不恢复、隔离或调整发送阈值。
3. 比较两个同权限、同风险方案：真实SoD整体正确标定的原评分，以及仅加预先声明事件条件的同评分。不能只比较“旧外生日程门限”与“新SoD门限”。
4. 只测试式(4)单次历史载荷替换，保留未检出和零报警；不扩展攻击类型。
5. 观察条件虚警差异、总体虚警与检测能力，而不是用补偿MSE作为主证据。

**OPEN。** 现有材料没有提供这一被动原Yang、真实SoD评分的独立校准/测试证据；原序贯缓存标定来自不同策略，E2/E3固定日程亦不能补齐。本轮不生成数据，也不通过重用旧研究样本冒充新确认性验证。

**停止条件。** 若整体同分布重标定即可解决虚警，而条件分组在相同风险/信息下没有可解释的检出价值，则应停止把它作为独立论文创新。若精确积分需要接收端不可见全网模式，则不能作为合法在线方案。若只能给普通Gaussian截断、标准秩标定或“多一个分组”，而无新增应用结论，不应以中文学报目标为由降低真实性要求。

## 10. 立项判断及四问回答

| 任务问题 | 审查回答 |
|---|---|
| 真实SoD是什么？ | 原预测估计与上次发送估计的平方距离>.12，或10步timeout；t0强制；即时可靠接收，raw缓存保持、A幂外推，无过期清理 |
| G1健康残差服从什么分布？ | 原代码用经验联合矩评分而非精确密度；被动原Yang在固定外生日程下Gaussian，真实SoD下一般是截断Gaussian的线性像/其混合；存在精确Gaussian例外 |
| 正常SoD是否造成选择效应？ | 是。模式指示函数改变原始噪声律；已有矩阵首步hold协方差迹改变约26.53%，send分支恰不变 |
| 原G1是否已解决？ | 已处理相关prefix、经验episode最大值标定，并诚实声明近似；未建立真实SoD精确条件风险，不能直接迁移旧门限 |

| 候选命题 | 结果与贡献边界 |
|---|---|
| 命题1 | 已给完整有限时域选择分布推导及实际矩阵例子；一般原理已有，未证明新的可计算闭式族 |
| 命题2 | 自动严格保证不成立；精确同分布总体分位数仍有效。未证明原冻结最终门限在真实SoD实测超标 |
| 命题3 | 对新部署严格保证需补同分布/独立单位标定；条件化阈值并非必需，功效提升未证明 |

**最终建议：NO-GO。**

理由不是要求顶级期刊难度，也不是要求每个应用都发明新统计工具，而是本轮尚不能支持“发现并修复原G1遗漏的SoD统计缺陷”这一论文主张：

- 选择效应早在G1审计和相关文献中已指出。
- 原G1已避免直接依赖独立χ²阈值，使用经验标定；不能搭建一个不存在的弱基线。
- 本轮确认的跨日程、跨估计策略迁移与有限样本边界，可以用标准独立校准处理。
- 尚无同目标健康SoD标定强基线下的检测增量，更没有将其与单次历史替换联系起来的额外保证。
- 本轮首步结果包含保守化和独立例外，不能据非Gaussian一般性预设虚警必然膨胀、修正必然提高检出。

这份报告可以作为工程正确性与统计边界材料，但当前不足以按新检测方法立项普通中文学报论文。没有凭E3 No-Go更换研究主线；没有自行启动其他方向。后续是否做一项限定验证或补充文献，由负责人另行决定。

## 附录A：确定性复算说明

只读取已冻结NPZ，不导入engine/model，不调用随机数生成器。下列矩阵公式复现第5节；积分为确定性Gaussian球截断积分。

~~~python
import numpy as np
from scipy.integrate import quad
from scipy.stats import norm

path = ("reviews/g1r_risk_constrained_recovery/results/"
        "g1r_replay_joint_20261114_r01/replay_joint_matrices.npz")
with np.load(path, allow_pickle=False) as d:
    A, H0, H1, K = d["A"], d["H"][0], d["H"][1], d["gains"][0, 0]

P, Q, R = np.eye(2), .02*np.eye(2), .05*np.eye(2)
VX = K @ (H0 @ P @ H0.T + R) @ K.T
VY = H1 @ (A @ P @ A.T + Q) @ H1.T + R
CYX = H1 @ A @ P @ H0.T @ K.T
lam, U = np.linalg.eigh(VX)
den = 2*np.pi*np.sqrt(np.linalg.det(VX))
delta = .12

def angular(phi):
    c, s = np.cos(phi), np.sin(phi)
    a = c*c/lam[0] + s*s/lam[1]
    b = a*delta/2
    p = -np.expm1(-b)/a
    m = 2*(1-(1+b)*np.exp(-b))/(a*a)
    return np.array([p, c*c*m, s*s*m])/den

vals = [quad(lambda phi: angular(phi)[j], 0, 2*np.pi,
             epsabs=1e-12, epsrel=1e-12) for j in range(3)]
p_hold = vals[0][0]
second = U @ np.diag([vals[1][0], vals[2][0]]) @ U.T
for name, B, conditional_X in [
    ("hold", np.zeros((2, 2)), second/p_hold),
    ("send", H1, (VX-second)/(1-p_hold)),
]:
    VR = VY+B@VX@B.T-CYX@B.T-B@CYX.T
    C = CYX-B@VX
    F = C @ np.linalg.inv(VX)
    conditional_R = VR-F@VX@F.T+F@conditional_X@F.T
    print(name, conditional_R, np.trace(conditional_R)/np.trace(VR))

# 第6.2节人工选择反例；不是原G1阈值的实测FPR
rho, c = .8, 1.
z = norm.ppf(.975)
sd = np.sqrt(1-rho*rho)
tail = lambda x: norm.sf((z-rho*x)/sd)+norm.cdf((-z-rho*x)/sd)
joint_send = 2*quad(lambda x: norm.pdf(x)*tail(x), c, np.inf,
                    epsabs=1e-12)[0]
joint_hold = quad(lambda x: norm.pdf(x)*tail(x), -c, c,
                   epsabs=1e-12)[0]
print(joint_send/(2*norm.sf(c)), joint_hold/(1-2*norm.sf(c)))
~~~

式(17)的实际首步hold单分量尾概率，用\(Y\mid X=x\sim
N(C_{YX}V_X^{-1}x,V_Y-C_{YX}V_X^{-1}C_{XY})\)，将其双侧Gaussian尾函数乘X密度，在\(\|x\|^2\le.12\)上极坐标积分，再除以p_hold。该积分在两套容差下均为0.020490151651764814。

## 附录B：证据与交付保护

| 资产 | SHA256 |
|---|---|
| simulation/engine.py | 05fb3f19d457e103d7c1665ccd1087ea4b27076d6a39b57ac7e0d16cfdb35c97 |
| simulation/model.py | 5b674a4cc274fca42d52d00f15490d5e3952231df98146a90cb28a62b4a9aeca |
| simulation/sequential_cache.py | dd9c8678544c98a481551528fbec60318b5e4bea94cc95ef2efe742470fdd6a8 |
| simulation/cache_monitor.py | 59615c7758f32306418e2c3f7f7341d09ec0bd58822cd39fdb34a727190014a4 |
| simulation/config.json | cf801650e2527a409ebb4730e894e6d3fcb3602a08259bfeda1cb529d7ebb62b |
| 联合NPZ | c02f7d0041fa568246d2788084fe2c78b9a5f912ab03166a0bb7830f3efa7c0a |
| G6-R0原报告 | 0cb189abcafccbedf4723df005c5e544837594e48ca5a7ba3a2c80f70656c115 |

**FACT，交付检查。** 143个受保护文件的SHA256前后相同，包含simulation顶层Python/JSON、G1-R报告及实现、G6-R0报告；所有报告内相对链接存在。git diff及暂存区差异为空，HEAD保持03a00789508755f1df9bf16dee901af37d7e34f1。本轮新增仅为G7报告目录；原有未跟踪文件保持原状。没有运行可能生成随机数据的测试脚本，数值核验仅为本报告列出的确定性积分和既有矩阵运算。

未修改旧报告、估计器、配置、E2/E3或G1/G1-R实现；未创建Run、未生成新轨迹、未重新校准、未开发完整检测器。本轮只保存本报告草稿，不commit、不push，完成后停止。

