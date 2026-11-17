# G8：原始 G1 论文立项与成果收束审查

日期：2026-11-16。研究执行助手提交的决策材料；最终立项决定由研究负责人和项目负责人作出。

**建议结论：NO-GO。现有材料不足以支撑一篇声称“单次历史链路 FDI 事后检测有可信性能增量”的普通中文学报方法论文。**

这不是否定缓存污染、后续量测或原始 G1 问题的价值，也不是要求顶级期刊理论。主要原因是：最强正面实验主要属于持续 FDI 下改变融合权重后的估计收益；已保存的单包 FDI 数据没有完成“原 Yang 不变、已融合后的后续量测带来增量、同风险强基线”的完整验证。动态 GLS、相关白化、CUSUM、跨包累积及经验最大值标定已经实现，不能重新命名成新算法。G7-R0 的 NO-GO、旧失败门槛和 E2/E3 的检测—恢复边界全部保留。

标记：**FACT**＝原报告/代码/数据支持；**DERIVED**＝对既有材料的确定性复算或数学推论；**HYPOTHESIS**＝尚未验证；**OPEN**＝证据缺口。文中的“正式”指已有登记、独立测试或正式Run，不表示其终点就是本轮检测问题。

## 1. 四个立项问题的直接回答

| 问题 | 回答及决定性证据 |
|---|---|
| 1. 已有结果能否支撑普通中文学报论文？ | **当前不足以支撑所冻结问题的增量方法论文。** 可形成可复核的实现、机制和负结果材料，但不能把它们升级为强基线优势。单包FDI的GLS筛选未显示稳定优势；持续FDI的GLS优势在完整协方差均值对照下未通过，序贯整体门槛也失败。见第5节。 |
| 2. 最有价值的单一贡献是什么？ | **把一次历史链路载荷偏差、反复缓存融合及后续接收端证据之间的关系落实为准确、可复核的模型与评价链。** 单次FDI全时域传播在48个已有Seed上验证到约2.02×10^-13；合法特征接口也已核验。这是可靠研究资产，但尚不足以独立宣布新检测算法或原创中心定理。 |
| 3. 相对静态GLS、单窗口检测及直接竞争是否有可信增量？ | **未建立。** 同一观测窗口、同一模型下，前缀动态模板GLS与对应批量GLS是同一统计；改变扫描时刻提供的是报警机会/延迟权衡。持续step下GLS对瞬时方法有局部收益，但对完整协方差均值只有0.30035%的归一化超额收益、Holm p=1；该试验仍非单包旁路检测。Deghat等未完成忠实同权限性能移植，不能宣布胜过它们。 |
| 4. 哪些结论有实验支持？ | **已支持：** 指定固定日程的缓存传播、已有检测/门控实现、若干持续FDI估计收益、单包FDI已知事件下的固定时刻报警记录。**未支持：** 单包FDI到达时漏检后的同风险增量检出率/检测延迟优势、一般未知事件定位优势、原Yang不变的完整强基线比较、真实闭环SoD。E2覆盖与E3恢复MSE不填补这些缺口。 |

**下一步唯一任务：由研究负责人审阅本报告并确认原始G1本轮成果收束及NO-GO。** 本轮不指定新方向、不设计新算法，也不安排补跑实验。当前不是仅缺一个置信区间或一项轻量对照；不能承诺“只补一个实验即可立项”。

## 2. 冻结问题与本轮操作范围

### 2.1 固定研究问题

- 原有 Yang-form 分布式估计器及其名义增益保持不变。
- 单条通信链路、一次历史发送载荷的加性FDI；攻击结束后该载荷仍留在接收缓存中，被多次使用。
- 接收端只使用合法收到的历史包、本地时钟、后续本地量测/创新及公开模型。
- 通信限已有证据支持的公共外生日程或相同信息权限下的可观测间歇日程。**观察到一个SoD日程，不等于其噪声条件分布可按外生日程处理；本轮不宣称真实闭环SoD已验证。**
- 不增加恢复、隐私、强化学习、DoS、丢包、动态拓扑或Replay分类任务。
- 检测器旁路输出告警，不通过报警改变融合权重、裁剪、发送或内部状态。

**DERIVED。** 为避免混用时窗，令r为攻击包接收时刻、q为下一次覆盖该边缓存的时刻：

1. **到达检测：** 在r使用当拍可用信息；
2. **缓存驻留事后检测：** r<d<q，恶意原包尚在缓存；
3. **退出缓存后检测：** d≥q，原包已替换，但网络估计可能仍有历史污染。

三者都可研究，但不是同一任务。证明第3类存在污染，不能代替第2类的检测优势；第2类使用更多量测胜过单点，也不能直接证明胜过同信息静态GLS。

**范围约束。** 本轮不额外要求未知事件定位，也不把“到达时已经被某检测器漏检”强加为所有试验的筛选条件。已知待检查的接收包可以是合法研究设定，但对照必须有同样先验。只有论文进一步声称弥补到达检测的漏检时，才需要共同冻结的到达检测规则及相应条件评价；“已参与融合”本身不等于“经某规则判为正常”。

### 2.2 工作区、证据版本与只读纪律

**FACT。** 使用 GitHub 对应隔离分支 g1r-e2-status-contract-20261115；本地与远程HEAD均为：

    788204a388155c9604348fc09d6ce510691c3fc4

远程为center-666/paper。开始时隔离工作区干净。未切换、合并、reset、rebase、提交或推送。

主工作区main仍为490e5b8...并有G5未提交改动。其G5内容不混作已发布结论，本轮不修改该工作区。为复算旧数字，只读访问了主工作区保留、但隔离分支未纳入Git的原实验CSV；其出处和哈希单列，不伪装成GitHub上完整归档的文件。

**FACT。** 本轮不运行旧实验或测试runner，不调用simulate/generate_data，不生成随机轨迹，不重新Bootstrap，不重新校准，不创建实验Run。对旧逐Seed CSV只做计数、均值和配对差算术。旧区间及p值从其原报告/结果读取，没有事后换指标重做显著性筛选。

## 3. 已有资产地图及继承结论

以下是与本轮问题有关的资产入口及证据用途。G1/G1-R核心代码和G6/G7原文继承同会话的读取与核查，本轮补核报告、计划、runner和原始数值；不把“读取审计报告”冒充重新执行其全部验收。

| 阶段 | 报告、实现、计划与正式结果入口 | 本轮继承什么；不继承什么 |
|---|---|---|
| 原始统计与参考门控 | [project_evidence.md](../fdi_replay_20261112/project_evidence.md)、[shared-data报告](../fdi_replay_20261112/evidence/prior_results/2026-11-10_shared_data_v2_REPORT.md)；simulation/calibration.py、run_study.py、reference_screen.py | 9项主要时间尾部标定增量0项通过；不能改称已获安全检测创新 |
| 缓存GLS探索 | [CACHE_SCREEN_REVIEW.md](../../simulation/checks/next_direction_diagnostics/CACHE_SCREEN_REVIEW.md)；[cache_exploration_plan.json](../../simulation/cache_exploration_plan.json)；cache_monitor.py、cache_screen.py | 含single_step；持续step局部有效，单包没有稳定优势；原策略有cap/隔离 |
| GLS强简单对照 | [确认报告](../../simulation/exploration_runs/2026-11-11_cache_mean_confirmation/REPORT.md)、plan.json、primary_tests.csv、output_audit.json；cache_aged_confirmation.py | 128新测试Seed，GLS对instant/mean主比较1/4通过 |
| 序贯强基线 | [分阶段报告](../fdi_replay_20261112/evidence/prior_results/2026-11-11_sequential_strong_v1_REPORT.md)；sequential_cache.py、run_sequential_validation.py、sequential_validation_plan.json；[主比较CSV](../../simulation/validation_runs/2026-11-11_sequential_strong_v1/primary_tests.csv) | 192Seed，12项5项通过但完整场景1/4；持续FDI估计终点，不是本轮单包检测成功 |
| 跨包CUSUM、部分观测压力 | [跨包报告](../fdi_replay_20261112/evidence/prior_results/2026-11-11_cusum_carry_v1_REPORT.md)、[压力报告](../fdi_replay_20261112/evidence/prior_results/2026-11-11_partial_observability_probe_v4_REPORT.md)；两个runner/plan及primary_tests.csv | 跨包step 3/4不撤销主门槛；压力主边0/4；反向边好结果不能替换主问题 |
| G1数学/停止审计 | [baseline_equivalence.md](../fdi_replay_20261112/baseline_equivalence.md)、[identifiability_audit.md](../fdi_replay_20261112/identifiability_audit.md)、g1_decision.md、g1_experiment_plan.md、g1_existing_code_audit.json | 完整协方差、共享缓存误差、信息饱和已有；不能改名重提 |
| G1-R早期传播/权限/单包记录 | [07传播](../g1_retroactive_recovery/07_full_horizon_propagation_audit.md)、[08权限](../g1_retroactive_recovery/08_information_permission_audit.md)、[09 Deghat映射](../g1_retroactive_recovery/09_deghat_discrete_baseline.md)；p0_verified.py、receiver_gls_writeback.py；results/g1r_p0_verified_20261113_v1/ | 单次FDI及Replay传播准确；合法本地接口；48Seed已知事件探索性报警，不是独立增量检测验收 |
| G1-R最终100Seed | [17预注册](../g1_retroactive_recovery/17_final_test_preregistration.md)、[18结果](../g1_retroactive_recovery/18_final_replay_results.md)、[20结项](../g1_retroactive_recovery/20_research_closeout_no_go.md)；results/g1r_final_analysis_20261113_v1/ | 是Replay、检测归责和恢复比较；91/100不能移作FDI检出率 |
| G1-R 01—12 | [目录](../g1r_risk_constrained_recovery/)、01范围/02数学/03合同/04计划/05竞争/06预注册/07联合模型/08预算/09风险细化/10v2/11求解权限/12公平性 | 固定日程统计基础与风险条件；不把正常补偿预算当检测虚警预算 |
| G1-R 13—20 | 同目录实现、预E2只读、确定性检查、状态合同、runner、执行计划、完整性及授权报告 | 实现可信性和冻结流程；不是算法性能增量 |
| 正式E2/E3，21—26 | [21 E2](../g1r_risk_constrained_recovery/21_e2_final_report_20261116.md)、[22独立覆盖](../g1r_risk_constrained_recovery/22_e2_independent_coverage_audit.md)、23—25准备与数学、[26 E3](../g1r_risk_constrained_recovery/26_e3_formal_experiment_report.md)及正式结果目录 | E2 PASS；E3 COMPLETED但NO_GO_PERFORMANCE。集合覆盖/补偿动作/真实MSE不同于本轮检测 |
| 27、B0 | [27诊断](../g1r_risk_constrained_recovery/27_e3_postmortem_and_next_decision_draft.md)、[28 B0](../g1r_risk_constrained_recovery/28_B0_identifiability_and_recovery_bound_audit.md) | 标准核条件、半径及风险界不自动形成独立创新；不重开理论方向 |
| G2 | g2_final_report.md、addendum、g2_screen_plan.json、simulation/g2_replay_runner.py；[最终勘误](../g2_closeout_errata/results/2026-11-13_g2_readonly_erratum_r01/g2_erratum_report.md)及逐Seed重析 | 9/48实际受攻，18.75%不是条件检测率；cap贡献不可归给检测器；未证强基线失效 |
| G3 | [冻结计划](../g3_partial_observability/g3_preregistered_plan.md)、[执行报告](../g3_partial_observability/execution_report.md)、plan.json、code/run_g3_pilot.py及Gate A结果 | 正常资格通过、Gate A未通过；Gate B后续信息试验未运行，不能说已证明后续量测无用 |
| G4 | 01竞争、02模型、03理论、[04最小恢复价值](../g4_topic_screen/04_minimal_value_of_recovery.md)、05排序；recovery_budget_probe.py、analysis及preregistration | 8旧Seed、67日程、64字节的恢复筛选；不用于FDI检测立项，也不重开其他方向 |
| G5 | [03决策](../g5_direct_competitor_audit/03_A_vs_F_decision.md)、01 Gao、02 Ye/Wang、04条件问题、EXECUTIVE_SUMMARY、公式核查 | 已发布版本的隐私/方向融合审查为旁支边界。旧缺全文状态是当时记录，不声称现在仍缺；不使用未提交G5修改来更新本轮结论 |
| G6 | [G6-R0](../g6_retrospective_detection/01_research_direction_audit.md) | 事后检测已有直接文献，不能主张首次；本轮不处理正常延迟分类 |
| G7 | [G7-R0](../g7_sod_conditioned_retrospective_detection/01_core_problem_audit.md) | **完整继承NO-GO**：选择分布、条件阈值、正确重标定不列为论文创新；本轮不以该方向挽救G1 |

**证据版本说明。** 后出的正式结果覆盖先前“尚未运行”的计划状态，但不改写旧文件。例如G3预注册写pending，实际以execution_report为准；E2报告当时写E3未执行，最新以26号为准。G5主工作区未提交材料与本隔离分支的发布版本分开。

## 4. 方法实现审计：公式、权限、时间、阈值、适用条件

### 4.1 原Yang及一次历史FDI

**FACT，engine.py。** 对节点i：
\[
\hat x_i(k+1)=A\hat x_i(k)+K_i(k)[y_i(k)-H_i\hat x_i(k)]
+\epsilon A\sum_{j\in N_i}(A^{a_{ji}(k)}q_{ji}-\hat x_i(k)).
\tag{1}
\]
新包先更新缓存，age0包影响下一估计状态k+1。健康不发送时raw载荷保持，融合输入继续按A幂外推。固定日程下，FDI在r令\(q_{ji}=\hat x_j(r)+b\)，r之后不再注入；到q之前该b仍被反复融合。

G1原始缓存残差（与本地innovation不同）：
\[
R_a=y_i(r+a)-H_iA^a q_{ji}
=H_iA^a(e_j(r)-b)+
\sum_{\ell=0}^{a-1}H_iA^{a-1-\ell}w_{r+\ell}+v_i(r+a),
\tag{2}
\]
\(e_j(r)=x_r-\hat x_j(r)\)。固定外生发送事件、独立未来噪声下，正常prefix协方差保留共享e_j与过程噪声：
\[
\Sigma_{ac}=H_iA^aP_e(A^c)^TH_i^T+
\sum_{\ell<\min(a,c)}H_iA^{a-1-\ell}Q(A^{c-1-\ell})^TH_i^T+
1_{a=c}R_i.
\tag{3}
\]
不能把每次融合视为新的独立邻居观测。若改用自身innovation或跟踪q之后的污染，应使用既有全网/缓存传播响应，不只用\(H_iA^a\)。

### 4.2 实现矩阵

令\(d_L=R_{0:L-1}-\hat\mu_L\)、\(C_L=[I,\ldots,I]/L\)、\(M_L=\operatorname{col}(H_i,H_iA,\ldots,H_iA^{L-1})\)。

| 方法 | 数学定义和已实现位置 | 合法输入与判定时刻 | 阈值及边界 |
|---|---|---|---|
| 到达时空间检测packet_spatial | 当前残差Mahalanobis量；CacheMonitor.packet_thresholds及MonitorController | 当前本地y、实收包、H；仅age0判定 | 正常age0分数经验分位，后续保持门控；与每个prefix都检测不是相同报警机会 |
| 每拍瞬时缓存检测instant_cache/instant | \((R_{L-1}-\mu_{L-1})^T\Sigma_{LL}^{-1}(R_{L-1}-\mu_{L-1})\) | 当前本地y与A^age缓存；每个age | 已按整个episode最大值校准，不能把它描述为只有收包时才能检测 |
| 联合窗口能量joint_cache | \(d_L^T\hat\Sigma_L^{-1}d_L\)；cache_monitor.py | 完整合法缓存prefix | 全协方差、ridge及样本不足fallback；非独立卡方逐点阈值 |
| 动态模板GLS gls_cache | \(Q_L=d_L^T\Sigma^{-1}M_L(M_L^T\Sigma^{-1}M_L)^\dagger M_L^T\Sigma^{-1}d_L\)；CacheMonitor.fit的白化SVD投影 | 同一prefix、本地y、实收缓存、公开A/H；逐age重算 | 经验episode最大值；模板GLS**已实现**，不是G8新算法 |
| 完整协方差均值mean_cache/mean | \(d_L^TC_L^T(C_L\hat\Sigma_LC_L^T)^{-1}C_Ld_L\)；CacheMonitor及PhaseStatistics | 同一prefix；每age | 算术平均但保留完整均值协方差；一般不等于最优常量GLS，不应弱化成独立样本平均 |
| 因果窗口白化white_window | \(z_\ell=[\operatorname{chol}(\hat\Sigma_{\ell+1})^{-1}]_{\rm last}d_{\ell+1}\)，\(W_a=\sum_{\ell=\max(0,a-w+1)}^a\|z_\ell\|^2\) | 只用当前/过去prefix；过去z不因未来到来回写；w=4 | 正常episode最大值；独立高斯仅是特定模型解释，代码不作实际保证 |
| 能量CUSUM | \(C_a=\max(0,C_{a-1}+\|z_a\|^2-m)\) | 合法白化prefix；在线逐age | 正常最大值+正常tune；m为量测维数；非简单独立卡方公式 |
| 双侧有符号CUSUM | \(C_a^\pm=\max(0,C_{a-1}^\pm\pm z_a-\kappa)\)，对分量和正负方向取max，\(\kappa=.5\) | 同上 | 同类经验标定；符号方向并非新机制 |
| 跨包证据 | carry_across_packets=True，新包重置prefix/能量但保留CUSUM；报警后清零累计量 | 已有每次实收包及后续残差；不需要新通信 | run_carry_cusum_audit已运行；统计状态不保证新包间独立 |
| 固定事件全窗口GLS | p0_verified.py：公开网络响应J、\(\hat\theta=(J^TPJ)^{-1}J^TPd\)、score=\(\hat\theta^TJ^TPJ\hat\theta\) | receiver本地innovation，可选实收缓存分歧；在d一次判定 | 已知待检事件、正常64训练/48校准；与纯缓存\(M_L\)及未知事件scan不同 |
| 未知事件搜索 | receiver_gls_writeback.py candidates_from_receptions/attribute：实际接收事件字典、各J、最大score | 固定d，合法接收历史和本地innovation | 整个候选最大值正常标定；已有最终Replay试验，不能新称“首次未知定位” |

**FACT。** PhaseStatistics按initial/transient/steady、edge、当前prefix长度拟合矩；足够样本时全协方差，fallback为块对角且明确标记。训练和校准只用完整episode；末尾删失单列。CacheMonitor早期筛选的episode处理包含终端截断，后续sequential排除未闭合episode，风险口径不能混算。

**FACT。** 基础门限用正常episode所有prefix最大值的95%经验分位数，后续sequential用独立tune数据四轮调整，再独立audit/test；carry版本使用独立tune的二分控制。既有代码不承诺任意轨迹/每份校准集都严格5%，也没有直接将各时刻视为独立χ²。G7已给有限样本秩、依赖和迁移边界；本轮不把这些改写为创新。

### 4.3 是否保持原Yang

**FACT。** 缓存筛选/序贯runner实际调用method="capped"及cache_monitor；controller返回隔离与age衰减权重，报警会影响后续估计、发送者轨迹和残差。它们的MSE正面结果是**检测—门控—估计闭环结果**，不是原Yang不变的被动检测结果。

p0_verified.py的Log.update返回全1，已核对logger与vanilla Yang状态差为0；这个数据生成端符合原Yang不变。但是它的主要评价为后续影子补偿MSE，固定d/已知事件报警也不是完整的“到达未检出后逐步报警”比较。

**DERIVED。** G8不应把旧controller直接接回engine来声称“只是读残差”：它的返回值会改变融合。现有离线评分函数可复用，但本轮不实现新的被动包装器。

### 4.4 与“静态GLS”的关系必须说清

“静态GLS”没有一个天然唯一含义，本报告分别比较：

- **单点GLS/空间检验：** 只用r时刻；后续prefix确有更多数据，但效果必须控制报警机会和误报风险。
- **固定窗口批量GLS：** 与动态prefix在同一L、同一M/Σ、同一数据下，公式完全一致。令\(s=M^T\Sigma^{-1}d\)、\(I=M^T\Sigma^{-1}M\)，两者都是\(s^TI^\dagger s\)。递推实现、逐prefix评估不是自动的统计增量。
- **静态常量偏置模板：** 采用\(\mathbf1\otimes I\)而不是HA模板；是模板不同，需要数值强基线比较，不能拿错误独立协方差当唯一对照。
- **全信息单窗口检测：** 应得到相同合法时刻/通道。若候选多用一段量测或缓存分歧，收益可能只是信息量增加，不能直接归为算法优越。

**DERIVED / STANDARD。** 固定Gaussian均值偏移模型中，增加后续块的设计信息为
\[
I_{L+1}-I_L=
\widetilde M^TS^{-1}\widetilde M\succeq0,
\quad
\widetilde M=M_+-C^T\Sigma_L^{-1}M_L,
\quad S=\Sigma_+-C^T\Sigma_L^{-1}C.
\tag{4}
\]
它解释后续量测何时增加条件信息，但这是标准Schur补结果，G1/G6已有分析。增加信息不保证每个实际扫描检测器在调整门限后功效上升。共享缓存自然误差也会造成饱和：G1标量例已有\(I_L=L/(\sigma_v^2+L\sigma_e^2)\to1/\sigma_e^2\)。本轮不包装新定理。

## 5. 最强实验结果及其与冻结问题的距离

### 5.1 单包FDI的原缓存GLS筛选：没有稳定优势

**FACT / DERIVED。** 原Run为2026-11-11_cache_episode_screen_v1，两个模型、128独立测试Seed；single_step只注入首个真实发送机会。指标仍为状态201—250接收MSE，策略有cap/隔离。

定义候选G与基线B的配对超额差：
\[
d_s=(J_{G,a,s}-J_{G,0,s})-(J_{B,a,s}-J_{B,0,s}),\quad
g=-\bar d/\bar J_{B,0}.
\tag{5}
\]
它不是检出概率，也不是相对受攻MSE的百分比。

| 模型/攻击 | GLS对instant的g | 旧探索性95%区间（超额差d） | 解释 |
|---|---:|---:|---|
| 原模型，单包FDI | +0.022916% | [−0.0000648,+0.0000082] | 极小，区间跨零 |
| 异质模型，单包FDI | **−0.027082%** | [−0.0000845,+0.0001802] | 点估计不利GLS，区间跨零 |
| 异质模型，持续step | +7.277700% | [−0.0174278,−0.0092151] | 局部正面，属于持续注入与门控MSE |

原报告位置：[CACHE_SCREEN_REVIEW.md第2—7节](../../simulation/checks/next_direction_diagnostics/CACHE_SCREEN_REVIEW.md)。本轮只读本地原始11,520行per_seed_metrics.csv，重新算出单包差−0.0000230971966281（原模型）、+0.0000493597850157（异质模型），与报告一致。没有重新生成区间。

**重要边界。** 该结果不能证明所有单包FDI检测无效；它证明目前这组旧试验并没有显示可用的单包估计收益。不能把持续step的7.28%复制进G8单包结论。

### 5.2 GLS相对强简单基线：主门槛1/4

**FACT。** 新128测试Seed的2026-11-11_cache_mean_confirmation，在异质模型对instant和完整协方差mean做四项预设比较：

| 场景/对照 | 接收超额改善/基线健康MSE | 接收总受攻MSE相对改善 | Holm p | 原门槛 |
|---|---:|---:|---:|---|
| step / instant | 9.329620% | 5.285050% | 0.00497063 | 通过 |
| step / mean | **0.300352%** | 0.115873% | 1 | 未通过 |
| half_step / instant | 0.908597% | 0.028025% | 1 | 未通过 |
| half_step / mean | 0.118972% | −0.005515% | 1 | 未通过 |

来源：[primary_tests.csv](../../simulation/exploration_runs/2026-11-11_cache_mean_confirmation/primary_tests.csv)、[REPORT.md](../../simulation/exploration_runs/2026-11-11_cache_mean_confirmation/REPORT.md)、plan.json。step/mean配对超额差区间为[−0.00170103,+0.00045769]；没有证明动态模板超出强简单均值。

**FACT。** output_audit.json记70个case、8960行、MSE重算最大误差0、源哈希及划分检查通过。实现可靠与原门槛失败同时成立。本试验未包含single_step，不能当作冻结单包问题的正式确认。

### 5.3 序贯对照：有窄正面，但完整门槛失败

**FACT。** 2026-11-11_sequential_strong_v1共192独立测试Seed，12个主比较5项通过，四个完整日程×场景单元仅irregular+step通过，原要求至少两个。原判定为失败。

持续step下mean相对三基线的接收总MSE改善：

| 日程 | white_window | white_cusum | white_signed_cusum |
|---|---:|---:|---:|
| gap8 | 4.8830% | 4.8449% | 2.7360%（Holm后未过） |
| irregular | 8.6741% | 7.0884% | 6.7925% |

同一irregular+step的接收MSE均值为mean 0.2686466616、window 0.2941624836、energy CUSUM 0.2891421548、signed CUSUM 0.2882243090。本轮从本地26,880行旧CSV重新求均值，与GitHub主比较一致。

half_step下没有相同收益：gap8分别−0.2728%、−0.3935%、−1.0351%；irregular分别+0.2805%、+0.3792%、−0.1891%，六项均未过。来源：[主比较](../../simulation/validation_runs/2026-11-11_sequential_strong_v1/primary_tests.csv)、[贡献门槛](../../simulation/validation_runs/2026-11-11_sequential_strong_v1/contribution_gate.json)。

**FACT。** 独立输出审计已核140case、26,880行、192Seed，MSE复算误差0，22,710个Schur/prefix检查最大统计差约2.04×10^-13。本轮没有重跑该审计。它证明保存结果与实现一致，不证明新颖性。

**FACT。** 跨包CUSUM补充试验192Seed，mean对energy/signed在gap8改善3.9099%/1.9326%，irregular改善5.0710%/3.3706%，四项3项过。其half_step只有约−0.22%至+0.33%；不能覆盖原主门槛或改为单包结论。部分观测压力主边四项0项过，Holm p均1；不选择有利反向边改写。

### 5.4 原Yang不变、单次FDI的48Seed记录：真实但尚不足

**FACT。** P0最终验收参数：r=200、q=208、d=216、固定gap8、b=[1.2,−0.8]；64训练、48正常校准、48测试，既有Seed被重复用于调试/修复后的探索性验收，不是新独立确认。

数据生成采用raw Yang，Log返回全1；全时域传播与完整仿真比较：

- FDI状态最大绝对差2.01889042593×10^-13；
- FDI对齐缓存最大差2.02446688428×10^-13；
- 48Seed、状态201—280；验收的FDI/Replay两场景合计76,800个节点分量行和153,600个缓存分量行，不能把合计数都记在FDI名下；
- 纯预测器不读未来真实状态，允许后续真实发送包含网络反馈污染。

来源：[验收JSON](../g1_retroactive_recovery/results/g1r_p0_verified_20261113_v1/acceptance.json)、[p0_verified.py](../g1_retroactive_recovery/code/p0_verified.py)、[07传播报告](../g1_retroactive_recovery/07_full_horizon_propagation_audit.md)。

本轮从576行原始per_seed_metrics.csv独立计数：

| 输入/窗口 | FDI固定时刻报警 | 健康报警 | 受攻报警而健康配对不报 |
|---|---:|---:|---:|
| 本地innovation，200—216 | 9/48（18.75%） | 2/48 | 8/48 |
| innovation＋缓存分歧，200—216 | **48/48（100%）** | 3/48 | 45/48 |
| 本地innovation，209—216 | 1/48（2.083%） | 1/48 | 0/48 |
| innovation＋缓存分歧，209—216 | 3/48（6.25%） | 0/48 | 3/48 |

来源：[per_seed_metrics.csv](../g1_retroactive_recovery/results/g1r_p0_verified_20261113_v1/per_seed_metrics.csv)。第三列/第四列不是重新定义成功标准；配对告警不一致仅为解释记录，不能直接称“新增量测造成的因果检出”。

**不能将48/48写成G8优势，原因具体如下。**

1. 它在预先给定事件r和固定d上评分，不能扩写为未知事件搜索优势；已知事件本身可以作为G8设定，但尚缺同先验的强基线对照。
2. 全窗包含r；缓存分歧在r有直接攻击馈入，innovation在r尚未受该包影响。100%未分离后续量测的贡献，也不能进一步说明“r时漏检后靠未来量测补检”。
3. 两组输入不同：加缓存分歧带来额外信息；未与同信息强基线比较。
4. 正常报警分别3/48、2/48、1/48、0/48，不能称实际相同误报率；它们也不是同时/全轨迹保证。
5. 后窗209—216属于退出缓存后；不是r<d<q的驻留事后窗口。
6. 没有同风险、同先验的到达信息与增加后续信息的被动强基线对照，不能完成增量归因。若要进一步声称漏检补检，还需共同预定到达规则及漏检子集；本轮不把该额外主张默认为既有成果。

**DERIVED。** 该P0数据支持“合法历史特征可以形成报警，传播模型可实现”，不支持“已证明后续量测优于静态GLS/窗口/CUSUM”。它的主要数值收益又涉及影子恢复，不进入G8检测价值表。

### 5.5 E2/E3与其他方向：仅继承边界

| 阶段 | 已确认事实 | 对G8不能作的推断 |
|---|---|---|
| 100Seed最终Replay | 主场景91报警、85正确归责、6错归责、9未报警；正常10/100；回写与全网影子约3.42×10^-13等价 | 不能称单次FDI91%检出；恢复MSE下降不等于检测增量 |
| E2 | 共同影响集合主场景200/200覆盖、Set攻击非零136/200、正常非零0/200，PASS | 覆盖不是定位/检出；动作不是告警 |
| E3 | 原Yang9.8996305110、Hard9.6568284428、Soft9.6542652447、Set9.6618472242；Set相对Yang改善2.40194%；最终NO_GO_PERFORMANCE | 不用相对Yang恢复收益证明FDI检测，也不把完整运行说成实验不可靠 |
| G2勘误 | 自然策略仅9/48Seed替换；有告警的方法受攻后9/9出现过告警，但大量健康/攻击前报警；cap承担多数强Replay损失下降 | 18.75%不是条件检测率；后续任意告警不是正确归因 |
| G3 | 正常协作收益约90.609%，Gate A未证明要求的保护—信息代价，Gate B未运行 | 不说明后续信息无用；也没有可用于G8的已验证信息增量 |
| G4 | 8旧Seed、67日程、64字节额外广播，强基线oracle恢复改善约1.69%—1.91%，停止该实例 | 不转为主动通信或新恢复算法来支持本轮 |
| G5/G6/G7 | 各自保留明确停止/缺证据判断；G7原经验阈值并非独立卡方误用 | 不将SoD选择效应、隐私、附加信息或新阈值包装成G8贡献 |

## 6. 基线公平性审查

**DERIVED。** 当前证据存在以下相互独立的比较边界，不是简单补一个样本量即可修复。

| 公平性维度 | 已有做到的部分 | 对G8仍缺什么 |
|---|---|---|
| 单次/持续攻击 | 原cache筛选含single_step；P0单包明确 | 最强确认试验是持续step/half_step，不能替代单次历史FDI |
| 原估计器不变 | P0 raw Yang/logger等价通过 | GLS/mean/CUSUM强比较都含cap、age权重或隔离反馈 |
| 同信息 | 各缓存prefix对照共享联合矩；强简单mean已保留 | P0 local与cache输入不同；未有同权限全窗口/序贯比较 |
| 同判定机会 | 多prefix方法按episode最大值标定 | 到达单点、完整episode、固定d、未知事件最大值须分别核定风险单位 |
| 正常风险 | 独立正常开发、audit、test，经验率完整保存 | 不能把目标5%、实际约5%、严格边际5%混同；P0小样本各方法风险不同 |
| 首警与持续报警 | 某些episode保存alarm/max | bad状态持续为真不是新首警；缺冻结单包子问题的统一首警对照 |
| 健康配对 | 原实验按Seed配对，部分超额差单列 | 配对MSE与告警因果贡献不同；不能用少数迟到报警代替功效 |
| 实验独立性 |128/192独立测试有注册/源哈希 | P0修复沿用测试；同Seed多事件/年龄/episode不能增大独立样本数 |
| 决策规则 | 原失败门槛及低幅/压力结果保留 | 本轮不得挑持续强偏置、换边、改MSE/检测指标“挽救” |
| 强文献 | 完成多篇公式级审查 | 未完成同Yang协议忠实实现，不能声称击败Deghat等 |

**关键区分。** 旧MSE门槛未过并不数学否定新的检测问题；反过来，未测检测问题也不能把旧MSE有利点认作检测创新。本轮NO-GO来自**缺乏对应冻结问题的可信增量证据**及标准方法重合，而非把旧1%/5%MSE阈值硬搬成新检测指标。

## 7. 竞争文献对照：只继承既有审计，不新检索

本轮没有新增文献搜索或下载。以下页码/公式以各既有审计所注明读本为准，不混淆作者稿与正式版。没有文献题名不同即可认定创新的推断。

| 直接竞争 | 已有公式级结论 | G8剩余差异及不能声称的事 |
|---|---|---|
| Deghat等2019 | G1-R早期09号：式(12)(13)本地innovation＋邻居分歧，(18)联合误差/攻击跟踪，Thm2 LMI保证；需要额外辅助误差估计交换 | 离散缓存、直接攻击输出通道及辅助通信尚未忠实适配。不能把标准GLS叫Deghat，也不能说它不处理链路偏置；差异不自动构成新增能力 |
| Tabatabaei等2025 | G1-R 01/05、G6矩阵：级联观测器，式(12)—(15)重构状态/输出/攻击，Thm3.1/3.2附条件 | 物理耦合与邻居输出信息不同；不提供本项目免费强基线，亦不能只凭不同模型宣称新颖 |
| Gupta等2026 | G1-R05：攻击条件KF，(15)(16)未知起点混合，历史依赖阈值Thm3及G-CUSUM | 已有相关创新/历史起点序贯检测。补充证明未独立取得；不能声称现有方法只看即时残差 |
| Mao等2026 | G1-R05：邻居原始量测、多模型概率、(36)—(43)后验融合/CI | 不同信息权限且改变估计器；不能据其多模型名称宣称G8新，也不能把恢复对照当检测对照 |
| Qian等2023 | G7第8节：创新触发、Gaussian近似Assumption2、截断条件矩与估计更新 | 条件统计已有；G8明确不走SoD阈值创新 |
| Qiu等2019 | G7第8节：触发误差进入式(6)(7)残差，H∞/H∞残差与阈值 | 事件相关阈值已非新点；其有界能量保证不能直接换成Gaussian概率保证 |
| Liang–Liu2023 | G1 baseline_equivalence、G7：物理MAS输出ZOH、UIO、触发误差阈值 | 不是同一共同状态Yang缓存接口，不能免费用其假设；“保持旧数据+邻居残差”也已有先例 |
| Han等2015 | G7：随机指数二次触发保持Gaussian，精确条件MMSE | 与本轮固定间歇日程不同；不得改发送机制后称原问题解决 |
| Tunga等2018 | G1/G6/G7：窗口χ²、CUSUM、误报警与隐蔽攻击影响分析 | 白化、窗口与累积均属成熟工具；已有G1强对照不能删除 |
| Zhang等2022/2023反向检测 | G6-R0第7节：固定点平滑器、后续输出估计历史等效增量、反向残差和检测条件 | “数据已入闭环后用后续信息检测过去”一般思想已有；G8不作首次事后检测宣称 |

审计入口：[G1文献精读](../fdi_replay_20261112/literature_reading_notes.md)、[Deghat映射](../g1_retroactive_recovery/09_deghat_discrete_baseline.md)、[Gupta/Mao全文审查](../g1r_risk_constrained_recovery/05_quickdet_palmdkf_fulltext_audit.md)、[G6-R0](../g6_retrospective_detection/01_research_direction_audit.md)、[G7-R0](../g7_sod_conditioned_retrospective_detection/01_core_problem_audit.md)。

**OPEN。** 部分既有审计保留全文/证明缺口，不能称穷尽式排重。**本轮提出必须补充的论文：0篇。** 当前停止决定已由同框架强基线、冻结单包问题的证据缺口决定，补文献不是关键阻塞；不以等待全文拖延明确NO-GO。

## 8. 论文贡献能怎样诚实表述

### 8.1 可保留的单一成果表述

> 在固定间歇通信和原Yang-form更新下，建立并核验一次历史链路载荷偏差在邻居缓存和网络估计中的持续传播，明确接收端可用于后续验证的合法残差及其跨时相关性，并通过已有强基线比较界定累计证据的有效范围。

**证据性质。** 前半句有代码/传播与权限验收支持；后半句主要是已有标准检测机制的比较及失败边界。它可用于项目成果收束、方法实现说明、复现实验或诚实的研究素材；目前没有足够单包检测增量支持把它包装成新算法论文主贡献。

| 可写 | 不可写 |
|---|---|
| 单次载荷注入会在停止后继续经缓存参与融合；后续新包也可能带反馈污染 | 攻击停止后所有新包立即健康，或删除旧包就消除历史影响 |
| 动态模板GLS、相关mean、窗口/CUSUM均已实现，并做过多个强基线比较 | G8首次提出GLS、窗口白化、跨包累积或最大值校准 |
| 指定持续强FDI场景有局部估计收益 | 对本轮单包FDI已证明同风险事后检出优势 |
| P0有单次FDI报警数据，但已知事件/窗口/输入权限有限 | 48/48即证明对未知事件、到达漏检后的普遍100%检出 |
| E3运行可信、Set恢复收益存在但未胜强基线 | E2通过或Set相对Yang改善证明检测机制优于传统方法 |
| G7指出统计迁移边界，保持NO-GO | SoD条件分布或新分组阈值是本论文核心创新 |

**判断标准。** 普通中文学报不必要求新优化范式或顶级难度定理；一个小而明确、同权限同风险下可重复的检测收益也有可能支撑论文。问题是当前并没有对应冻结范围的这条完整证据链。不能把科研投入轮数或工程完备程度作为算法增量替代物。

## 9. 关键证据缺口：不是只差一个最小实验

1. **攻击终点缺口：** 正面确认结果集中于持续FDI；单包已有弱/负结果。
2. **不干预估计器缺口：** 主要强基线比较都含cap/age/隔离；raw Yang数据只有不同用途的P0固定时刻探索。
3. **新增信息归因缺口：** 缺同时匹配窗口、输入、事件先验与正常风险的批量GLS/窗口/CUSUM比较。
4. **时刻信息分解缺口：** 全窗成绩未区分到达时刻直接证据与后续证据。若主张漏检补检，才另需共同冻结到达规则的条件评价；不能事后挑有利Seed，也不将该额外主张作为本问题必需的新要求。
5. **指标缺口：** 缺统一首警延迟、到达后限定窗检出概率和未检出的删失口径；不能靠持续bad状态或恢复MSE补齐。
6. **独立性与数据完整性缺口：** P0测试复用；部分早期原始CSV未进GitHub，仅本地可查，审阅者不能仅凭GitHub重建所有表。

**停止规则执行。** 因不止一项缺口，不能标成“只需补一项就可以立项”的CONDITIONAL GO。也不通过设计新的窗口、扩大幅值、调整门限、换方向/链路、增加算法来寻找正结果。本报告不安排或执行任何新增实验。

如果负责人以后重新授权同一冻结问题的验证，必须先确认接受何种已有方法作为候选、统一风险终点和公平比较；那是新的明确研究授权，本轮不以“建议最小实验”替代它。

## 10. Go/No-Go和下一步唯一任务

**研究建议：NO-GO。**

它否定的是“凭当前已经完成的G1工作，可以诚实地宣称冻结单包FDI事后检测存在可发表的方法增量”这一当前判断，不是否定所有未来可能结果，也不切换研究方向。

**下一步唯一任务：研究负责人审核并确认成果收束。** 审阅重点为：

- 是否接受持续FDI正面结果不能替代单包检测证据；
- 是否接受动态GLS相对完整协方差均值的失败结果；
- 是否接受P0 48/48的输入、窗口、事件先验和风险限制；
- 是否同意本轮保持NO-GO、不自动运行补充实验。

没有新方案名称、论文题目、仿真计划或Seed申请。本轮到报告交付为止。

## 附录A：只读复算与来源完整性

### A.1 GitHub与本地补充数据

隔离分支保存了计划、报告、主比较CSV和审计JSON，但若干旧Run的全量逐SeedCSV/轨迹没有纳入Git。具体：

- GitHub可直接访问：缓存GLS只读复查报告；mean确认primary_tests；sequential/carry/partial主比较与门槛；P0逐Seed指标和传播表。
- 本地补充：C:/Users/zhongxin/shixidoc/mypaper/simulation/exploration_runs/2026-11-11_cache_episode_screen_v1/per_seed_metrics.csv；
  C:/Users/zhongxin/shixidoc/mypaper/simulation/validation_runs/2026-11-11_sequential_strong_v1/per_seed_metrics.csv。
- 不将这些本地数据的可访问性写成GitHub全部原始文件齐全；本轮不复制大文件、不修改旧归档。

本地与隔离分支的mean确认/sequential/carry主比较CSV初次字节哈希不同，经核查仅为CRLF与LF；按UTF-8-sig读取后全部字段、行和规范化文本一致。没有以此误报数据损坏。

### A.2 本轮复算了什么

- 对P0共576行、每方法/场景48Seed的flag计数和健康配对告警一致性。
- 从本地缓存筛选11,520行，重算single_step与step的接收均值及式(5)配对超额差。
- 从本地序贯26,880行，重算irregular下各方法受攻MSE均值。
- 读取原主比较中的p值、区间、passes并核对原gate。
- 没有新随机Bootstrap；没有导入运行器并调用其main；没有把读取结果文件视为生成实验。

### A.3 关键文件 SHA256

| 文件 | SHA256 |
|---|---|
| GitHub缓存筛选复查报告 | fd0e5bffa2e3b9c4041534691c01529814d61c6138f769c86dfbf5f59cee90b5 |
| GitHub mean确认primary_tests.csv | 79902e0668552a4ee2f72012fbf90c04454178fe376652515b3e2f002ad7a8c1 |
| GitHub sequential主比较CSV | 5129713e064769dff3a98ab99d840268bc1f68ddfa4790e01a6c438dfdc20bbb |
| P0逐Seed CSV | b554beae65b1cd0834f35d34923a1d3f8d9d0d4807f0f019a364323b94bc7dde |
| P0实现p0_verified.py | 9c573da0e1b89c57bd2d5e3649f3b9a0f6a6765d0cc3e8aea4c679eb61bf8b05 |
| 本地缓存筛选11,520行CSV | 34f69edae95b932ac28c120f8321ef475831f8dd413bbad9cdd595079f51bbe4 |
| 本地序贯26,880行CSV | fd3910190c6aa8fdc594e7012f5e2b54f37dc526c0fdcecaadeb864b7393a33d |

## 附录B：交付纪律

交付前核验298个受保护文件SHA256，零变化；保护范围包含核心代码、配置、各阶段报告/代码及主工作区G5文件。44个报告相对链接均有效。已跟踪文件和暂存区均无差异，HEAD未变；本轮新增仅此G8报告草稿。

旧失败结果、G7 NO-GO、G1-R/E2/E3正式记录不改。禁止事项均保持：无新随机轨迹、无仿真、无重新校准、无实验Run、无新检测/补偿算法，无engine/model/冻结配置修改，无G2/G5写入，无Git提交/推送。后续由研究负责人明确指令决定。

