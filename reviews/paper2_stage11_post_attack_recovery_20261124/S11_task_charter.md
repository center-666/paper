# S11 任务书：有限持续时间攻击后的可信审计与估计恢复

版本 0.1，2026-11-24。本文冻结研究范围、通信/攻击合同和首轮实验门槛。它不是已完成理论、算法或性能结果。本轮只建立任务书，不修改既有研究代码，也不生成随机性能样本。

## 1. 研究目标

研究事件触发状态估计中，有限持续时间的发送载荷篡改如何由可信事件与有限码字记录进行全时域审计，以及攻击结束后如何选择性重处理历史并恢复状态估计。

暂定题目为 **事件触发有限比特上行下有限持续时间虚假数据注入的可信审计与估计恢复**。主线为有限码字联合核、攻击区间置信集、选择性历史重处理和条件风险约束输出。论文目标控制为三项：

1. 有限饱和均匀量化、可信事件及发送后载荷注入下的序贯概率核与共同协方差位置混合递推。
2. 未知起点、有限持续时间、未知常值注入下的全时域候选置信与参数盒排除。
3. 置信攻击区间驱动的历史重处理与条件风险约束双支路输出。

软融合须通过独立 MSE 门槛。若无独立收益，保留风险约束的 monitor/recovery 支路选择。

## 2. 已有成果与证据边界

| 来源 | 本任务中的作用 | 证据边界 |
|---|---|---|
| Stage 3、Stage 6 联合事件核与 V2 | 推导起点、二维单通道、共同协方差分量结构 | 原载荷连续 |
| Stage 9 累计证书与双支路代码 | 证书来源和恢复工程接口参考 | 旧观测核为连续载荷 |
| R4a 参考鞅 | 全时域 Ville 覆盖与参数盒排除模板 | 有限码字核和有限结束攻击需重新实现 |
| R4a-Final 数值审查 | 来源日志、尾部码和区间审计经验 | binary64 一次舍入不同于 S11 有限均匀量化 |
| 2026-11-21 恢复试验 | 反面基线和设计约束 | 持续攻击、旧 phase 协议、连续载荷，不是 S11 性能数据 |

既有 160,000 episode 试验中，S1 在 512 拍下各攻击报警率约 0.025%–0.05%，大多接近健康误报率。S1 episode-start hard rollback 与固定 50/50 融合没有测得 MSE 改善。U1 过期检查点回滚 MSE 达 \(2.45\times10^{14}\) 至 \(1.93\times10^{15}\)，monitor 约为 0.144 至 0.163。它们提示 checkpoint freshness 必须受限，不是 S11 的有限码字性能证据。[旧恢复试验分析](../paper1_audit_recovery_theory_20261121/recovery_trial/results/run_v1/results_analysis.md)

## 3. 系统与通信合同

### 3.1 主模型

\[
x_{t+1}=Ax_t+w_t,\quad y_t=Cx_t+v_t,\quad x_0\sim\mathcal N(0,P_0),
\]
其中 \(w_t\sim\mathcal N(0,Q)\)、\(v_t\sim\mathcal N(0,R)\)，与初值、phase 和触发随机数独立。

V2 主模型：
\[
A_{\rm V2}=\begin{bmatrix}1.02&0.10\\0&0.97\end{bmatrix},\
C=[1,0],\ Q=0.05I_2,\ R=0.20,\ P_0=0.8I_2,\ Z=2,\ W=I_2.
\]
观测矩阵行列式为 \(0.10\)，系统含不稳定模态。

稳定压力模型：
\[
A_{\rm S}=\begin{bmatrix}0.97&0.10\\0&0.93\end{bmatrix}
\]
并沿用其他参数。它可观测，协方差和收缩界须重新验证。[V2 模型](../paper2_stage6_vector_correction_20261122/model.json)

### 3.2 中心、事件和 monitor

保留随机相位预测反馈。monitor prior 产生 \(p_t=C\hat m_t^{M,-}\)。本拍事件前独立生成 \(\phi_t\sim{\rm Unif}[-\delta_q,\delta_q)\)，形成共同中心
\[
c_t=\phi_t+2\delta_q\left\lfloor
\frac{p_t-\phi_t+\delta_q}{2\delta_q}\right\rfloor ,
\]
V2 中 \(\delta_q=0.011628232298833967\)。phase 和 center 均写日志，sender/receiver 使用同一重构值。本轮有限字合同只针对上行 payload code；center/phase 沿用现有可信反馈接口并单独核算成本。未冻结 center/phase 的实际编码前，不声称端到端总通信字数有限。

令 \(r_t=y_t-c_t\)。可信事件满足
\[
\Pr(\gamma_t=0\mid y_t,c_t)=e^{-Zr_t^2/2},\qquad
g(r_t)=1-e^{-Zr_t^2/2}.
\]
event 先于攻击产生，触发随机数独立。攻击不能修改 event、phase、center、codec 或 receiver log。

在本任务主协议中，monitor 是唯一驱动未来 center/event 的递归支路；recovery 和融合输出只改变 receiver 对外发布的估计，不回写 sensor feedback，也不改变真实 event 序列。这样 Stage 3/9 的观测 filtration 可沿用。若以后让 recovery 估计反过来驱动 center，必须重推联合事件核和 R4 confidence process。

定义 \(S_t=CP_t^-C^\top+R,\ \sigma_t=\sqrt{S_t}\)。由于 covariance 只随公开 event 历史变化，两端可同步计算 \(\sigma_t\)。取 \(K_1=P_t^-C^\top/S_t\)、\(K_0=P_t^-C^\top/(S_t+Z^{-1})\)。monitor send 时以 \(c_t+\sigma_t\ell_j\) 更新，silent 时以 \(c_t\) 作伪观测更新：
\[
\hat m_t^{M,+}=\hat m_t^{M,-}
+K_{\gamma_t}(\tilde y_t-C\hat m_t^{M,-}),\quad
P_t^+=(I-K_{\gamma_t}C)P_t^-,\quad
P_{t+1}^-=AP_t^+A^\top+Q.
\]
monitor reconstruction 是工程 estimate。candidate likelihood 必须积分真实 code cell，不能把重构码当连续真实创新。

### 3.3 有限 bit 上行 payload

主精度 8 bit，敏感性 12 bit。固定 \(\kappa=4,\ K_B=2^B,\ \Delta_B=2\kappa/K_B\)。send 前的 codec 输入是
\[
u_t=(r_t+a_t)/\sigma_t.
\]
重构级 \(\ell_j=-\kappa+(j+\frac12)\Delta_B\)。code cells：
\[
J_0=(-\infty,-\kappa+\Delta_B),\quad
J_j=[-\kappa+j\Delta_B,-\kappa+(j+1)\Delta_B),\ 1\le j\le K_B-2,
\]
\[
J_{K_B-1}=[\kappa-\Delta_B,\infty).
\]
outer codes 是 saturation cells，包含两端高斯尾。receiver 解码为 \(c_t+\sigma_t\ell_j\)。silent 不产生 payload code。8/12 bit 只指 send code，event、center/phase feedback bit-rate 分别列出。

### 3.4 攻击权限

固定候选 \(\theta=(k,D,b)\)：\(k\ge0\)，\(D\in\{1,\ldots,60\}\)，\(\tau=k+D-1\)，
\[
b\in[-0.25,-0.10]\cup[0.10,0.25],\qquad
a_t=b\,\mathbf1_{\{k\le t\le\tau\}}.
\]
注入只在 trusted send event 后加到量化输入，一次攻击内幅值固定、时间连续。health \(H_0\) 单独建模并进入恢复风险集合。DoS、event forgery、center/phase tampering、replay、多段攻击及逐拍自适应幅值不属于目标类。

## 4. 三项待验收命题

这些是验收目标，不是当前已得结论。

### P1：finite-code 联合核与混合后验

候选 state prior 写成
\[
p_\theta(x_t\mid\mathcal F_{t-1})=
\int \mathcal N(x_t;m,P_t^-)\pi^-_{\theta,t}(dm).
\]
对分量 \(m\)，令 \(\nu=Cm-c_t\)。send code \(j\) 的联合质量应为
\[
q_{\theta,t}(1,j\mid m)=
\int_{\sigma_tJ_j-a_t}\phi_{S_t}(r-\nu)g(r)\,dr.
\]
silent mass 为
\[
q_{\theta,t}(0\mid m)=
\frac{\exp[-(Cm-c_t)^2/(2(S_t+Z^{-1}))]}{\sqrt{1+ZS_t}}.
\]
须证明对完整码字表求和后两者总质量为 1，包含两侧 saturation codes。send posterior 要对平移单元内 latent innovation 积分；静默按指数二次核重加权。每个分量 covariance 可由 event history 共用，完整后验还含均值混合协方差。

### P2：全时域攻击区间置信

\(P_0\) 为 health law，\(P_\theta\) 为固定攻击候选，\(L_t^\theta=p_\theta(o_{0:t})/p_0(o_{0:t})\)。reference template 取 \(D\in\{20,60\}\)、\(b\in\{-0.25,-0.10,0.10,0.25\}\)，onset prior \(w_k=1/((k+1)(k+2))\)，模板内 duration/amplitude 等权。未来 onset 质量为 \(1/(t+2)\)。所有模板使用相同 center/event/codec。

令 \(\lambda_D=1/2,\lambda_b=1/4\)，reference process 冻结为
\[
R_t=\sum_{k=0}^{t}w_k
\sum_{D\in\{20,60\}}\lambda_D
\sum_{b\in\{-0.25,-0.10,0.10,0.25\}}\lambda_b
L_t^{(k,D,b)}+\frac1{t+2}.
\]
因 \(\sum_{k=0}^tw_k+1/(t+2)=1\)，这是 onset/duration/amplitude 模板路径的 proper mixture likelihood ratio。离散 reference bias grid 不必含连续 true \(b\)。

初始 \(\alpha=\varepsilon=0.01\)，候选 confidence set 为
\[
\mathcal C_t=\{\theta:L_t^\theta\ge\varepsilon R_t\}.
\]
目标为证明
\[
P_0(\exists t:R_t\ge1/\alpha)\le\alpha,\qquad
P_\theta(\exists t:L_t^\theta<\varepsilon R_t)\le\varepsilon.
\]
整个参数盒只有在 likelihood upper \(<\varepsilon\) 乘 reference lower 时才能排除。固定真候选的 simultaneous-in-time coverage 不等于对所有 \(\theta\) 同一事件的族同时覆盖。

### P3：历史重处理和条件风险输出

每步保存 monitor checkpoint。置信集给出 \(k_t^-=\min k\)、\(\tau_t^+=\max\tau\)。recovery 从 \(k_t^--1\) checkpoint 开始，suspect window 内擦除 send code，窗口外使用实际 code；使用日志中的真实 center/phase，不从 recovery state 重造 feedback。擦除 payload 仍保留在 audit log，candidate likelihood 和风险按完整可见记录计算。recovery recursion 是确定性 reprocess estimate，不自动称为 Bayes posterior。

令 \(\mathcal C_t^{started}=\{\theta\in\mathcal C_t:k\le t\}\)。若该集合为空，不启动 replay。若其中有 surviving \(\tau\ge t\)，标记 stop unconfirmed。只有全部已启动 survivors 满足 \(\tau<t\) 时才称当前攻击区间停止已认证。checkpoint 位于最早可能 onset 前；在 coverage event 上，suspect window 覆盖真实攻击区间。

对固定 \(\theta\)，令 \(\mu_t^\theta=E_\theta[x_t\mid\mathcal F_t]\)、\(\Sigma_t^\theta=\mathrm{Cov}_\theta(x_t\mid\mathcal F_t)\)。两条记录可测的估计和融合满足
\[
J_t(w;\theta)=\mathrm{tr}(W\Sigma_t^\theta)+
\|\mu_t^\theta-[w\hat x_t^M+(1-w)\hat x_t^R]\|_W^2.
\]
先用共同 full-record filtration 推导，再与旧 cross-covariance 公式核对。risk envelope over \(\mathcal C_t\cup\{H_0\}\) minimizes over \(w\in[0,1]\)。由于 monitor \(w=1\) 在可选集，最坏 conditional risk upper 不劣于同一候选集合下 monitor upper。此 conditional statement 不等于 unconditional expected MSE gain；confidence failure event 代价需单列。

## 5. 每拍接口与失败行为

输入：版本化模型、monitor prior/posterior、event covariance、phase/center、event bit、send code index、quantizer version、时间戳和 source hash。

输出：monitor/recovery/selected estimate、alarm/confidence 状态、surviving onset/end envelope、conditional risk upper、fusion weight、saturation flag、每步耗时与内存。

状态至少包括 MONITOR_ONLY、AUDIT_ACTIVE、STOP_UNCONFIRMED、REPLAY_READY、RISK_GATE_REJECTED、RECOVERY_OUTPUT。分母无法证正、区间运算失败、来源错配或节点预算耗尽都返回未决，不能签发排除/恢复证书。

## 6. 对照、终点和确认样本

五个主对照：
1. Quantized Monitor。
2. 相同健康误报预算下 event-only audit + Monitor。
3. 相同误报预算下 GLR/CUSUM + Monitor。
4. alarm 后从 episode-start checkpoint hard rollback/replay。
5. finite-bit audit + selective replay + risk-constrained selection/fusion。

Oracle 使用真实 \(k,D\) 擦除真实攻击窗口，只作上界。固定 50/50 只作消融。方法共用相同 monitor-driven center/event/code trajectory。

主 episode metric：
\[
L_i^{post}=\sum_{s=\tau_i+1}^{\tau_i+512}
(x_s-\hat x_s)^\top W(x_s-\hat x_s),\quad
D_i=L_i^{Monitor,post}-L_i^{Proposed,post}.
\]
跨 preregistered cells 等权：\(\Delta=G^{-1}\sum_g E[D_g]\)。CI 采用按 cell 分层的 episode-level paired bootstrap，时间步不作为独立样本。

另外报告置信覆盖/错误排除、health false alarm、alarm/stop-certification delay、起止 interval coverage/width、攻击期与 post-stop MSE、health false-recovery cost、saturation rate、event rate、payload/feedback bits、runtime P50/P95/max、最大 branch count、outer width 和 unresolved rate。

## 7. 冻结首轮矩阵

| 子集 | 模型 | payload bit | \(b\) | duration | onset |
|---|---|---|---|---|---|
| 主实验 | V2 | 8 | \(\pm0.10,\pm0.25\) | 20,60 | 固定 80 / uniform integer 40–120 |
| 稳定压力 | \(A_S\) | 8 | \(\pm0.25\) | 20,60 | uniform integer 40–120 |
| bit sensitivity | V2 | 12 | \(\pm0.25\) | 20,60 | uniform integer 40–120 |

攻击轨迹运行到真实 \(\tau+512\)。健康对照按其配对攻击 episode 的 sham onset/duration 使用同一评估窗口，以便估健康误恢复代价。Pilot 每 cell 200 episodes，只估 variance/runtime，不进入 confirmation。确认样本量目标为主配对差 95% CI 半宽不超过 pilot attack-cell Monitor-vs-clean post-stop excess 的 10%。若该 excess 非正或不能稳定估计，则暂停 confirmation 并重审 meaningful-effect 标尺。每 cell 最少 500、最多 2000；达到上限仍不够精确就报告不确定，不继续抽样到显著。健康 alarm \(\alpha=0.01\)，候选 exclusion \(\varepsilon=0.01\)。阈值、模板、样本量、seeds、环境和删失规则在 confirmation 前冻结。

## 8. 阶段门和停止标准

| Gate | 验收 |
|---|---|
| S11-0 | 本任务书、机器可读协议、来源清单；本轮仅此交付 |
| S11-1 | code-cell 分割、饱和尾质量、归一化、混合后验和 2–5 拍独立积分 |
| S11-2 | Ville coverage、H0 e-alarm、finite-duration likelihood 和 box outer bound |
| S11-3 | fresh checkpoint、selective replay、full-record conditional risk |
| S11-4 | post-stop paired MSE 95% CI 下端 \(>0\)，health false-recovery CI 上端 \(\le0.015\) |
| S11-5 | soft fusion 相对 hard branch selection 有独立显著收益，否则删除 |
| S11-6 | 直接近邻全文公式级审查后才写原创性主张 |

V2 主攻击族下 confidence implementation 须符合 1% 错排预算。至少一个预注册攻击强度/持续时间层的 stop-after paired MSE CI 下端大于零，才主张工程恢复收益。停止认证延迟或 unresolved rate 导致主矩阵失效时，先返工模型/算法，不扩大样本。

## 9. 风险和实现顺序

- 有限 code alphabet 不消除 latent innovation 区间积分和 state mean mixture branch growth；合并分支必须保持概率和状态外包。
- 两个饱和 code 是半无限积分域，尾部不能丢弃后重归一。
- center 是 monitor 历史生成的公开控制。recovery 用真实日志 center；完整候选 risk filter 条件于 center/event/code 全记录。
- R4a theorem 可作证明模板，binary64 likelihood 和 continuous-payload samples 不能当 finite-bit 验证。
- \(A_S\) 是新增压力模型，所有相应协方差界须重算。
- 条件风险上界不自动推出总体 MSE 改善；失败事件代价与状态矩另行界定。

首轮顺序：实现 quantizer 与日志；验证归一和短时递推；固定候选做 2–5 拍独立积分；完成 finite-duration likelihood/reference process；通过审计 gate 后再实现 replay/risk/fusion；最后才启动冻结 pilot。

本轮没有开始 S11 代码、pilot 或性能试验。任务书选定的 \(\kappa=4\)、stable stress、攻击类和参考模板属于执行假设，变更须在随机确认实验前作版本化 amendment。
