# G3执行记录：正常资格通过，Gate A pilot未通过后停止

2026-11-13。冻结基准为提交 `ce5923164aee083769eb5f5b2bfb8af1c4585124` 中的 [plan.json](plan.json)。原计划、门槛、旧结构记录、G1/G1-R/G2运行及共享代码未修改。本报告不替换预注册文本中的历史“尚未执行”状态；实际状态以本报告和新Run为准。

**EXPERIMENTAL：本轮按预注册停止G3当前筛选，不进入Gate B，不运行confirm，不开发新防御。原因是未证明预先要求的“保护增益与至少5%正常信息损失”同时出现；并非原Yang正常失稳或协作信息没有价值。** 当前也没有证明强基线完全覆盖该场景，更没有证明后续合法信息无用。

## 1. 实际执行范围和不可更改项

|阶段|Run ID|状态|
|---|---|---|
|确定性正常资格及独立engine基底核查|`2026-11-13_g3_normal_eligibility_r01`|通过|
|48正常fit、48正常threshold、24预注册pilot、Gate A|`2026-11-13_g3_pilot_gate_a_r01`|执行后停止，门槛未通过|
|原pilot轨迹的只读补充指标|`2026-11-13_g3_stopped_pilot_report_r01`|完成，不重跑仿真|
|Gate B固定诊断的12训练/12screen|—|未运行；A未通过|
|32seed confirm|—|未运行；前置条件未通过|

模型、H几何、主边0→1、固定不规则外生日程、名义增益、两条Replay规则及全部seed均使用冻结计划。没有改为反向边、改噪声、调攻击强度或扩大seed。正常控制二分最多12轮，只使用11600000段48个fit和11700000段48个threshold种子；pilot为11800000—11800023。两个模型均完整保留不利结果，满秩参考不能挽救partial失败。当前Zhou为项目既有机制适配，非原论文完整性能复现。

## 2. 精确正常协方差及核查

**DERIVED/标准线性理论：** 定义节点误差 \(e_i(t)=x(t)-\hat x_i(t)\)，边缓存接收前对齐误差 \(c_{ji}(t)=x(t)-A^{t-\ell_{ji}}m_{ji}(\ell_{ji})\)。在健康固定外生日程下，fresh边以 \(e_j(t)\) 替换该边误差。令该接收映射为 \(D_t\)，则

\[
\begin{aligned}
e_i(t+1)&=(A-K_i(t)H_i-\epsilon d_i A)e_i(t)
 +\epsilon A\sum_{j\in\mathcal N_i}(D_tz_t)_{ji}+w_t-K_i(t)v_{i,t},\\
c_{ji}(t+1)&=A(D_tz_t)_{ji}+w_t,\\
z_{t+1}&=M_tz_t+Lw_t+V_tv_t.
\end{aligned}
\]

所有节点和缓存块共享同一个 \(w_t\)，故其过程噪声协方差是 \(\mathbf1_{15}\mathbf1_{15}^{\mathsf T}\otimes Q\)，而不是独立分块Q。量测噪声仅通过当前节点的 \(-K_i v_i\) 注入，后续相关性由全矩阵递推传播。初始各节点估计/缓存均为0，\(P_z(0)=\mathbf1_{15}\mathbf1_{15}^{\mathsf T}\otimes P_0\)。因此

\[
P_z(t+1)=M_tP_z(t)M_t^{\mathsf T}+LQL^{\mathsf T}+V_t\operatorname{diag}(R_i)V_t^{\mathsf T}
\]

是当前固定日程、线性raw Yang下的真实无条件误差协方差，不是仅报告的名义Riccati矩阵。未将这条标准递推当成创新。

独立核查在真实accepted engine中传播前8拍的全部98个确定性初值/过程/量测噪声基底，逐步计算其Gram矩阵，与30维完整协方差全部分块比较。不是随机Monte Carlo，也没有用仿真误差轨迹给递推器输入。age=0消息按原engine当拍生效。

|量测几何|receiver尾窗比|network尾窗比|最小增广P特征值|独立基底最大误差|资格|
|---|---:|---:|---:|---:|---|
|partial|0.984950|0.991792|−2.02×10⁻¹⁵|6.66×10⁻¹⁶|通过1.10界及−10⁻⁹浮点PSD界|
|full-rank reference|0.982547|0.987725|−5.13×10⁻¹⁶|4.44×10⁻¹⁶|通过|

尾窗为状态350—399对300—349；这里只通过有限窗资格，未证明无限时域稳定。精确正常receiver平均MSE在状态51—200为partial raw0.245328、local3.616535。该解析平均值没有替代预注册的pilot/confirm种子区间要求。

## 3. 正常校准与协作资格

partial的cap为1.2071513；Zhou control为5.6568542，空间control为1.2418578。在正常threshold数据中，完整episode拒绝率分别4.706%、4.779%，分别于4轮和7轮内达到原5%±0.5百分点目标。没有读取pilot攻击数据回写控制量。

partial pilot的raw相对local正常receiver收益为90.609%，seed-bootstrap 95%区间[84.316%,93.877%]，大于10%下界。full-rank参考收益为27.677%，区间[20.177%,34.233%]。因此当前停止原因不是“无协作收益”。confirm未运行，不能宣称该资格已经独立重复。

pilot正常完整episode风险如下。区间按24个seed重采样，不能把2040个episode当独立样本。

|几何|Zhou正常拒绝|空间正常拒绝|
|---|---:|---:|
|partial|4.412% [3.529%,5.441%]|6.225% [4.755%,7.892%]|
|full-rank reference|5.196% [4.314%,6.078%]|6.618% [5.490%,7.745%]|

测试拒绝率相差超过1个百分点，且区间未确认可比，因此不得宣称同误拒绝风险下的检测性能排名。预注册没有允许因此重调pilot阈值，本轮没有重调。正常episode长度、右删失记录已保存：每个模型2040个完整episode，长度1/2/3/4/6/8对应192/192/600/408/432/216个；另24个末尾右删失episode不进入完整episode风险分母。

## 4. Gate A实际结果与停止原因

设 \(D\) 为partial pilot raw正常receiver MSE，\(D=0.259803\)。以下均用预注册19项族的同时区间，不是挑选单项普通95%区间。

|比较/统计|相对D点估计|同时区间|预注册要求|
|---|---:|---:|---|
|cap正常−raw正常|−0.335%|[−1.105%,0.107%]|上界≤5%，通过|
|Zhou正常−cap正常|4.789%|[1.131%,9.805%]|下界≥5%，未通过，区间不够精确|
|空间正常−cap正常|−0.569%|[−5.458%,6.129%]|下界≥5%，未通过；点估计没有正常损失|
|固定8包：cap攻击超额|522.194%|[358.449%,721.559%]|下界≥20%，通过|
|最近邻：cap攻击超额|403.608%|[254.143%,603.549%]|下界≥20%，通过|
|固定8包：cap−Zhou受攻MSE|502.268%|[333.864%,702.258%]|下界≥10%，通过|
|最近邻：cap−Zhou受攻MSE|347.247%|[200.402%,542.545%]|下界≥10%，通过|

空间门控也降低了cap受攻MSE，但两个门控都没有证明同一对照的正常代价下界达到5%D。故两条Replay规则的A均未通过；不得扩样寻找显著或更改5%实用门槛。

同时，不能把它写成“已有方法已解决全部问题”：固定8包下Zhou的攻击超额区间跨过10%D界；最近邻下Zhou攻击超额下界仍为14.799%D、空间为139.459%D；部分恢复区间也跨过10%D。原计划要求实际证实保护—信息代价权衡，而不是只发现尚有误差。这两个判断必须分开。

五种失败原因逐项记录：

|可能原因|本轮证据|
|---|---|
|原正常估计器本身不稳定|未发现；有限窗正常资格通过；不作无限时域稳定定理|
|合作信息没有足够正常收益|不支持；pilot收益下界84.316%|
|现有安全防御已完整覆盖|没有证明；不能当作停止结论|
|统计区间不够精确/未出现预定实质权衡|是当前停止原因；尤其Zhou正常成本跨5%界，空间成本点估计非正|
|后续合法信息无增量辨识证据|未测试；Gate B按前置条件停止，不能写成否定证据|

## 5. 攻击和恢复损失：描述性完整保留

以下为partial的24seed均值，不是论文性能确认结论。所有网络方法同14次替换、相同真实发送机会；跨防御的实际历史载荷可能不同。

|方法|正常receiver MSE|固定8包攻击MSE|最近邻攻击MSE|固定8包恢复累计超额|最近邻恢复累计超额|
|---|---:|---:|---:|---:|---:|
|local|2.76650|5.31012|5.31012|0|0|
|raw Yang|0.25980|398.61527|12.70753|2056.90124|22.46293|
|cap-only|0.25893|1.55188|1.24379|9.52535|6.28176|
|cap+Zhou|0.27137|0.24698|0.34164|0.23013|1.15555|
|cap+空间|0.25745|0.38457|0.95303|0.43732|4.51085|

恢复累计超额为状态251—300受攻减各自健康的平方误差和，允许负值；正部另列，不能混合。本表不是把raw→cap→检测的全部收益归给检测器。local不通信也不受该链路攻击，其攻击超额为0不等于绝对估计性能最佳。

恢复时间仅作描述：以状态251为起点，连续10状态满足原定平方误差容差后，在第10状态确认恢复；容差为该方法pilot正常MSE的10%，在confirm前已固定但本轮不执行confirm。partial raw固定8包/最近邻的受限平均确认时长为52.04/28.96拍，cap为22.33/20.38，Zhou为12.29/17.71，空间为14.50/19.92；这些组无右删失。未定义local的受攻恢复时间，记N/A。首次确认返回不保证随后永远不再超限。

所有网络方法503次节点广播、1006条边消息、16096个状态载荷字节/seed；local为0。没有额外验证消息。字节不含实际网络协议头。退出缓存后累计污染等指标见只读派生CSV；最后Replay包在tick246替换、tick250退出，影响后继状态从251计。后续包未经再次篡改，不意味着发送者已健康。

整体确定性资格运行约0.47s、正常校准及pilot约6.37s。未对每个算法单独计时，因此不作运行效率排名；CSV的trajectory_array_storage_bytes为离线轨迹数组存储，不冒充部署内存。字段network_receiver_clip_fraction_post_warmup计算的是网络全部边裁剪比例，按此实际定义解释。

## 6. 可复现与审计

- [正常资格脚本](code/run_normal_eligibility.py)、[正常资格汇总](results/2026-11-13_g3_normal_eligibility_r01/summary.json)、[独立基底检查](results/2026-11-13_g3_normal_eligibility_r01/deterministic_basis_checks.csv)。
- [冻结pilot runner](code/run_g3_pilot.py)、[停止决策JSON](results/2026-11-13_g3_pilot_gate_a_r01/summary.json)、[19项同时区间](results/2026-11-13_g3_pilot_gate_a_r01/gate_A_simultaneous_intervals.csv)、[原始逐seed指标](results/2026-11-13_g3_pilot_gate_a_r01/per_seed_metrics.csv)。
- [只读派生脚本](code/report_g3_pilot.py)、[完整派生指标](results/2026-11-13_g3_stopped_pilot_report_r01/derived_per_seed_metrics.csv)、[描述性汇总](results/2026-11-13_g3_stopped_pilot_report_r01/descriptive_method_summary.csv)、[episode风险及区间](results/2026-11-13_g3_stopped_pilot_report_r01/normal_episode_cluster_audit.csv)、[episode长度/删失](results/2026-11-13_g3_stopped_pilot_report_r01/episode_lengths_and_censoring.csv)。

每个Run保存配置、计划快照、原始依赖哈希、源码哈希和输出哈希；输入/轨迹/增益/完整联合协方差NPZ保存在对应Run中。所有原保护源在运行前后哈希相同，派生报告前后pilot文件也逐字节不变。Python语法及全部JSON结构已核查。归档NPZ受项目通用ignore影响，提交时应明确强制添加这些新Run的必要NPZ，不应用全仓库add。

独立复现使用全新Run ID，旧Run禁止覆盖：

```powershell
.venv/Scripts/python.exe reviews/g3_partial_observability/code/run_normal_eligibility.py --run-id g3_normal_reproduce_01
.venv/Scripts/python.exe reviews/g3_partial_observability/code/run_g3_pilot.py --run-id g3_pilot_reproduce_01
.venv/Scripts/python.exe reviews/g3_partial_observability/code/report_g3_pilot.py --run-id g3_readonly_report_reproduce_01
```

只读派生脚本明确读取本报告登记的原始pilot，不将复现结果混作新确认集；重复相同seed不增加证据量。

**研究衔接：当前G3筛选结束。A保留为一般研究问题，但本预注册实例没有获得新算法开发资格；B/C/D/F可由G4独立排重和小规模价值审查，不能借G4改变或重启当前G3门槛。** 本轮未下载文献。
