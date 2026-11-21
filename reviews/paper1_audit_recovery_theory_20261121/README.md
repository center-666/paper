# 量化可信事件审计驱动的估计恢复：理论推进包

基准提交：`8dddfbb9`。日期：2026-11-21。

本包在后置随机相位量化下推进序贯事件审计和估计恢复理论，并完成了 S1/U1 的 160,000-episode 固定协议试验。研究对象仍是标量、外生线性高斯远程估计。正式论文、既有量化研究包和大修候选均未修改。

## 当前核心结果

定义下一事件的相位平均健康静默概率
\[
\nu_t=\nu_\delta(P_t^+),
\qquad Y_{t+1}=\mathbf 1_{\{\gamma_{t+1}=0\}},
\qquad Z_{t+1}=\nu_t-Y_{t+1}.
\]

在健康运行下，\(Z_{t+1}\) 是条件均值为零、取值区间长度不超过1的鞅差；在攻击运行下，其条件漂移满足
\[
\mathbb E_\pi[Z_{t+1}\mid\mathcal F_t]
\ge \kappa D_t^2,
\qquad \kappa>0.
\]

因此阈值停止时刻
\[
\tau_h=\inf\{n:S_n\ge h\},\qquad S_n=\sum_{t=0}^{n-1}Z_{t+1}
\]
满足两类保证：健康下可用 Azuma--Hoeffding 控制误报；攻击下报警前的累计条件偏差能量满足
\[
\mathbb E_\pi\sum_{t<\tau_h\wedge N}D_t^2
\le \frac{h+1}{\kappa}.
\]

这条界把可信随机事件审计转成报警前条件偏差能量预算，但不直接给出完整 MSE 保证。新增条件风险恒等式明确指出，恢复还依赖检查点偏差及两支路误差关系。

恢复模块先采用两种可分析形式：

- 硬回滚：报警后停止使用污染普通支路，切换到可信检查点支路；
- 软融合：\(\hat x_t^r=(1-\alpha_t)\hat x_t^c+\alpha_t\hat x_t^a\)，按检查点风险、普通支路风险和交叉协方差选择 \(\alpha_t\)。

## 工程试验结论

固定时域阈值在 S1 下几乎没有检出力；最强的 U1 正向持续攻击设置也只在 0.45% 的 episode 中报警。S1 硬回滚和固定 50/50 融合没有降低测得攻击 MSE；U1 从 episode 起点开环外推的过期检查点导致巨大风险。漂移样本残差与理论条件漂移相容，但正漂移定理尚未转化为可用恢复算法。该结论延续了[后置相位单拍试验](../paper1_postcommit_phase_defense_20261121/README.md)的发现：总体TV可辨识并不保证有限样本能检出。

因此当前版本是**理论候选成立、工程方法未通过**。后续应提高有误报控制的事件信息利用率或延长有效观测时域，并为恢复支路设定可信检查点的新鲜度上限；不能据本轮结果声称量化安全算法有效。

## 研究边界

检查点恢复、间歇认证、攻击检测后切换、UIO 重构和多模型融合已有强近邻。候选增量只能落在：后置随机相位事件审计提供的污染风险预算，如何在同一攻击权限和本地可用日志下约束软融合/回滚的累计估计损伤。不能把“检测后回滚”或“自适应融合”单独包装为新算法。

本包不修改正式稿。试验时序和指标限制见 [trial_interpretation.md](recovery_trial/trial_interpretation.md)；完整结果和数值常数见 [试验报告](recovery_trial/results/run_v1/results_analysis.md)。

## 文件

- [范围与假设](00_scope_and_assumptions.md)
- [序贯审计定理](01_sequential_audit_theorem.md)
- [恢复规则与 MSE 界](02_recovery_rules_and_mse.md)
- [两轨估计条件风险恒等式](04_conditional_risk_identity.md)
- [文献边界与下一步](03_literature_boundary_and_next_gate.md)
- [确定性公式检查](check_formulas.py)
- [试验冻结协议、前置验证与代码](recovery_trial/protocol.json)、[前置验证结果](recovery_trial/pre_sampling_validation.json)、[运行环境记录](recovery_trial/execution_runtime.json)
- [原始试验数据与分析](recovery_trial/results/run_v1/summary.json)、[诊断重跑](recovery_trial/results/run_v1_diagnostic/summary.json)
- [交付核验](delivery_validation.json)
