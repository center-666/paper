# 持续正向发送后攻击：偏差与条件信息量核查

基准 `8cf49e73`。本文件核查阶段 2 附件与实际代码的对应关系，给出解析证明及确定性复算。没有生成随机样本，没有修改上一轮目录或正式稿。本文使用自然对数，信息量单位为 nat。

结论是：**不能给出每拍、几乎处处成立的正偏差下界或正 KL 下界；可以给出真实发送后的下一事件的正信息下界，以及任意时间块中发送机会的概率下界。** 后者足以建立一个按可信发送位门控的候选似然比和有限时间检测概率界，但目前保守常数不足以证明 512–2048 拍的实用检测功效。

## 1. 代码对应及分析变量

只读核查对象是 [run_trial.py](../paper1_audit_recovery_theory_20261121/recovery_trial/run_trial.py) 的 `persistent_positive_send`、`_update`、`D_a` 递推及 `_mean_silence`。

实际攻击为

\[
a_t=b\gamma_t\mathbf 1_{\{t\ge t_0\}},\qquad b>0,
\]

而不是静默时也能注入的常量输入。代码先根据真实量测与实际量化中心生成 `send_a`，随后使用 `action=np.where(send_a,b,0.0)`。`D_a` 更新中的另一个 `send_a` 与此重复相乘，但因为发送位为 0/1，并不改变模型。

令 \(\mathcal G_t\) 为动作已经提交、下一相位尚未抽取的扩充分析历史，包含真实**已发送**量测、实际可信事件与已公开相位；它不包含未发送真实量测或未来噪声。令

\[
\mu_t^+=\mathbb E[x_t\mid\mathcal G_t],\qquad
D_t=\mu_t^+-m_t^{a,+}.
\]

\(D_t\) 是 monitor 的条件均值偏差，既不是状态样本误差 \(x_t-m_t^{a,+}\)，也不是另一条独立健康运行与攻击运行的估计之差。两条反事实运行可能具有不同事件历史和协方差。

对 \(R_1=R\)、\(R_0=R+Z^{-1}\) 及 \(K_i(p)=p/(p+R_i)\)，实际递推为

\[
D_t=A[1-K_{\gamma_t}(P_t^-)]D_{t-1}
-\gamma_tK_1(P_t^-)b,\qquad t\ge t_0.
\tag{1}
\]

发送时真实量测项相消，只留下攻击项；静默时条件均值和 monitor 都使用同一个实际量化中心，该中心项也相消。S1/U1 的 \(A>0\)，攻击前 \(D_{t_0-1}=0\)。令 \(B_t=-D_t\)，则

\[
B_t=A[1-K_{\gamma_t}(P_t^-)]B_{t-1}
+\gamma_tK_1(P_t^-)b\ge0.
\tag{2}
\]

若改用生产支路生成传感器中心、变更静默更新、允许相位预知或状态反馈进入物理系统，不能直接复用该证明。

## 2. 附件中几何级数下界的两处问题

第一，\(0\le a_t\le\bar a<1\) 是传播系数上界，不能推出由 \(\bar a\) 组成的几何级数**下界**。即使假设每拍有 \(g_t\ge\underline g>0\)，取 \(a_t=0\) 就得到 \(B_t=\underline g b\)，小于附件所称的累积下界。若想获得 \(\underline g b\sum_{j=0}^{L-1}\underline a^j\)，需要另证 \(a_t\ge\underline a\ge0\)。

第二，原模型的注入系数是 \(g_t=\gamma_tK_1(P_t^-)\)，静默时严格为零，因此不存在每拍的 \(\underline g>0\)。

任意有限攻击后全静默前缀都有正概率。在该前缀上从未发生实际注入，故 \(B_t=0\)，下一事件的攻击分布等于健康条件基线。于是任何确定性等待时长后都不能宣称 \(B_t\ge d_{\min}>0\) 几乎处处成立。

即使此前已经发送，后续任意长静默段也有正概率；下文得到的 \(\rho<1\) 使该段上 \(B_{t+L}\le\rho^LB_t\to0\)。因此，“已经发生过攻击”同样不能修复逐拍严格正下界。有限静默段概率为正来自非退化高斯量测与严格正的静默核，不需要假设各拍独立。

## 3. Riccati 不变区间与发送后偏差下界

令

\[
f_r(p)=A^2\frac{rp}{p+r}+Q,
\quad
p_*(r)=\frac{-(r-Q-A^2r)+\sqrt{(r-Q-A^2r)^2+4Qr}}2.
\]

\(p_*(r)\) 是 \(f_r\) 的正不动点。取

\[
\underline p=p_*(R),\qquad
\overline p=\max\{P_0,p_*(R_0)\}.
\]

因为 \(f_R\le f_{R_0}\) 且二者均单调递增，\(P_0\ge\underline p\) 时归纳得到所有事件历史上的

\[
\underline p\le P_t^-\le\overline p.
\tag{3}
\]

这里 S1/U1 均满足前提，且 \(\overline p=0.8\)。定义

\[
k_- =\frac{\underline p}{\underline p+R},\quad
k_+ =\frac{\overline p}{\overline p+R},\quad
\rho=\frac{A R_0}{\underline p+R_0}.
\]

两模型 \(\rho<1\)，所以 \(0\le B_t\le k_+b/(1-\rho)\)。更重要的是，由式(2)，每次真实发送后均有

\[
\boxed{\gamma_t=1\ \Longrightarrow\ B_t\ge k_-b.}
\tag{4}
\]

这是一条发送条件下的下界，不是每拍下界。数值为：

| 模型 | \(\underline p\) | \(k_-\) | \(\rho\) | \(k_+\) |
|---|---:|---:|---:|---:|
| S1 | 0.0925406361 | 0.316334296 | 0.724253084 | 0.8 |
| U1 | 0.138514571 | 0.409183482 | 0.868201967 | 0.8 |

## 4. 发送后的下一事件：正概率偏移与信息下界

保留下一相位在当前攻击提交之后独立均匀抽取的协议。写

\[
V(P)=Z^{-1}+A^2P+Q+R,\quad s(P)=[ZV(P)]^{-1/2},
\]
\[
F_{\delta,V}(d)=\frac1{2\delta}\int_{-\delta}^{\delta}
\exp\left[-\frac{(d-e)^2}{2V}\right]de,\qquad
\nu_t=s(P_t^+)F_{\delta,V(P_t^+)}(0).
\]

新相位使实际量化误差在完整周期条件均匀，故下一静默位 \(Y_{t+1}=1-\gamma_{t+1}\) 满足

\[
p_t^a:=\mathbb E_\pi[Y_{t+1}\mid\mathcal G_t]
=s(P_t^+)F_{\delta,V(P_t^+)}(AB_t).
\tag{5}
\]

\(F\) 为偶函数且在正半轴严格递减。发送时 \(P_t^+=RK_1(P_t^-)\)，所以可取

\[
V_- = Z^{-1}+A^2Rk_-+Q+R,\qquad
V_+ = Z^{-1}+A^2Rk_++Q+R.
\]

置 \(d_b=Ak_-b\)。由式(4)及单调性，\(F(0)-F(AB_t)\ge F(0)-F(d_b)\)。对 \(0\le u\le d_b\)，

\[
-F'_{\delta,V}(u)
=e^{-(u^2+\delta^2)/(2V)}\frac{\sinh(u\delta/V)}\delta
\ge\frac{u}{V_+}
e^{-(d_b^2+\delta^2)/(2V_-)}.
\]

积分并用 \(s\ge1/\sqrt{ZV_+}\)，得到

\[
\boxed{
\gamma_t=1\ \Longrightarrow\
\nu_t-p_t^a\ge\epsilon_b
:=\frac{d_b^2}{2V_+\sqrt{ZV_+}}
\exp\left[-\frac{d_b^2+\delta^2}{2V_-}\right]>0.
}
\tag{6}
\]

该界直接作用于未归一化核差，不遗漏 \(F(0)\)，也不需要把全部攻击历史的最大偏差代入指数。\(b=0.25\) 的常数在本包重新计算，没有沿用旧 \(b_{\rm ref}=0.1\) 的数值合同。

发送时可以用

\[
\nu_-:=\frac{e^{-\delta^2/(2V_-)}}{\sqrt{ZV_+}}
\le\nu_t\le\nu_+:=\frac1{\sqrt{ZV_-}}.
\]

本包六组参数均满足 \(0<\epsilon_b<\nu_-\)。取 \(q_t=\nu_t-\epsilon_b\)，则 \(p_t^a\le q_t<\nu_t\)。定义

\[
v_b=\max_{u\in[\nu_--\epsilon_b,\nu_+]}u(1-u),\qquad
I_b=\frac{\epsilon_b^2}{2v_b}\ge2\epsilon_b^2>0.
\tag{7}
\]

Bernoulli KL 关于第一概率的二阶导数为 \(1/[u(1-u)]\)，故积分余项给出

\[
D_{\rm KL}(\operatorname{Bern}(q_t)\Vert\operatorname{Bern}(\nu_t))
\ge I_b.
\]

因 \(p_t^a\le q_t<\nu_t\)，实际条件 Bernoulli KL 也不小于此值。以上不等式在扩充历史逐路径成立，而候选 \(q_t\) 只用可信事件位、协方差标签与固定参数；通过条件期望塔式法则，可以传递到接收端可用的、尚未揭示下一相位的历史。

## 5. 实装候选接口与可预测发送门控

新 [core.py](core.py) 的 `probabilities` 和 [protocol.json](protocol.json) 实际使用当前发送增益，而不是把式(6)的固定最小偏移直接作为候选。对幅值 \(b_j\)，实装规则是

\[
q_t^{(j)}=
\begin{cases}
s(P_t^+)F_{\delta,V(P_t^+)}(A K_1(P_t^-)b_j),&\gamma_t=1,\\
\nu_t,&\gamma_t=0.
\end{cases}
\tag{8}
\]

代码传入的是负号 `-K*b_j`，因核为偶函数，与式(8)相同。这里 \(\gamma_t,P_t^+,K_1(P_t^-)\) 都在下一事件产生前可由可信事件串和已知模型确定。静默拍取 \(q_t=\nu_t\)，对应似然因子 1；这是明确的“无下注”步骤，故候选约束应允许 \(q_t=\nu_t\)，而不要求每拍严格小于。健康条件均值 \(\nu_t\) 正确时，每步因子的条件均值为 1，门控不损害健康鞅性质。

若实际攻击从候选起点以后持续存在，且 \(b\ge b_j\)，式(2)给出发送时 \(B_t\ge K_1(P_t^-)b\ge K_1(P_t^-)b_j\)，故 \(p_t^a\le q_t^{(j)}\)。进一步，式(4)–(6)给 \(q_t^{(j)}\le\nu_t-\epsilon_{b_j}\)。所以式(6)与式(7)的偏移/KL 下界同时适用于实装候选。因此无需知道确切强度，混合中保留不大于实际强度的候选即可。

理论上也可以使用更保守的固定最小偏移候选 \(\widetilde q_t^{(j)}=\nu_t-\gamma_t\epsilon_{b_j}\)。它只作解析对照，**不是当前实装规则**。因实装 \(q_t^{(j)}\) 可能更远离 \(\nu_t\)，该对照候选的对数取值范围不能拿来证明实装浓缩界。

令对应对数因子为

\[
\ell_{t+1}^{(j)}=Y_{t+1}\log\frac{q_t^{(j)}}{\nu_t}
+(1-Y_{t+1})\log\frac{1-q_t^{(j)}}{1-\nu_t}.
\]

其条件期望对真实静默概率严格递减，所以

\[
\mathbb E_\pi[\ell_{t+1}^{(j)}\mid\mathcal G_t]
\ge\gamma_t I_{b_j}.
\tag{9}
\]

若不门控而在完全静默、\(D_t=0\) 的路径上仍强制 \(q_t<\nu_t\)，此时真实下一事件概率等于 \(\nu_t\)，对数似然的期望是
\(-D_{\rm KL}(\operatorname{Bern}(\nu_t)\Vert\operatorname{Bern}(q_t))<0\)。因此不能借助“持续攻击”一词直接声称每拍正对数漂移。门控是得到此处保证的一种保守构造，不是最优检测器的证明；其他非门控候选可能有效，但需要单独分析失配代价。

## 6. 块发送机会与有限时间信息保证

给定时刻 \(t\) 事件产生前的历史（可含当前相位），真实量测预测方差为 \(P_t^-+R\)。高斯静默积分不大于 \([1+Z(P_t^-+R)]^{-1/2}\)，故

\[
\Pr_\pi(\gamma_t=1\mid\text{事件前历史})
\ge p_s:=1-[1+Z(\underline p+R)]^{-1/2}>0.
\tag{10}
\]

此界对所有攻击偏差成立。它不把事件串当成独立 Bernoulli 样本。迭代条件期望给出任意 \(L\) 拍动作块

\[
\Pr(\text{块内至少一次真实发送}\mid\text{块前历史})
\ge1-(1-p_s)^L.
\tag{11}
\]

相应下一事件审计须延伸到该动作块最后一拍之后。S1 的 \(p_s=0.205718893\)，14 拍块的机会下界超过 95%；U1 的 \(p_s=0.227800181\)，12 拍块超过 95%。这只是出现一次可审计注入的机会，不是块检测功效。

更一般地，令 \(M_n=\sum_{t=k}^{k+n-1}\gamma_t\)。对 \(0<r<p_s\)，逐步指数矩界
\(\mathbb E[e^{-\lambda\gamma_t}\mid\text{过去}]\le1-p_s+p_se^{-\lambda}\)
与 Chernoff 优化给

\[
\Pr(M_n<rn)\le
\exp[-nD_{\rm KL}(\operatorname{Bern}(r)\Vert\operatorname{Bern}(p_s))].
\tag{12}
\]

式(9)说明累计可预测对数漂移不小于 \(I_{b_j}M_n\)。下面为**实装候选**推导对数取值范围。由正负量化误差配对以及 \(\cosh\ge1\)，

\[
\frac{F_{\delta,V}(d)}{F_{\delta,V}(0)}
=e^{-d^2/(2V)}
\frac{\int_0^\delta e^{-e^2/(2V)}\cosh(de/V)\,de}
{\int_0^\delta e^{-e^2/(2V)}\,de}
\ge e^{-d^2/(2V)}.
\]

令

\[
\eta_j=\frac{(Ak_+b_j)^2}{2V_-},\qquad
c_j^+=\log\left[1+\frac{\nu_+}{1-\nu_+}(1-e^{-\eta_j})\right],
\qquad c_j=\eta_j+c_j^+.
\]

于是 \(q_t^{(j)}/\nu_t\ge e^{-\eta_j}\)，发送拍的对数因子位于 \([-\eta_j,c_j^+]\)，条件区间长度不超过 \(c_j\)；静默拍长度为零。该界使用 \(K\le k_+\)、\(V\ge V_-\) 和 \(\nu\le\nu_+\)，覆盖所有合法事件历史。

固定最小偏移对照候选另有更窄的区间长度界
\(\widetilde c_j=\log[1+\epsilon_{b_j}/(1-\nu_+)]-\log[1-\epsilon_{b_j}/\nu_-]\)，
在补充 [constants_actual_candidate.json](constants_actual_candidate.json) 中标记为 `constant_epsilon_candidate_only`，不得替换上面的实装 \(c_j\)。原冻结 [constants.json](constants.json) 的 `conditional_log_lr_range_upper_on_current_send` 字段属于这个固定最小偏移对照候选，**不是实装候选的区间界**；该原文件按冻结哈希保留，澄清见 [deterministic_correction.json](deterministic_correction.json)。

对未知起点/强度混合，若其中有效分量权重为 \(w_k\pi_j\)，置

\[
H_{k,j}=\log\frac1{\alpha w_k\pi_j}.
\]

这里 \(k\) 表示被攻击的**动作时刻**。实装 `Detectors.step(n,...)` 的第 \(n\) 次调用审计动作 \(n-1\)，因此动作起点 \(k\) 对应新分量权重 \(w_k=1/[(k+1)(k+2)]\)。若另用从 1 开始的审计起点下标，则相同权重写成 \(1/[j(j+1)]\)；两种下标不能混用。

混合统计量至少为 \(w_k\pi_jL_{k,k+n}^{(j)}\)。因此在 \(rnI_{b_j}>H_{k,j}\) 时，Hoeffding 鞅下尾界与式(12)联合给出

\[
\boxed{
\Pr_\pi(\tau_\alpha>k+n)
\le e^{-nD_{\rm KL}(r\Vert p_s)}
+\exp\left[-\frac{2(rnI_{b_j}-H_{k,j})^2}{nc_j^2}\right].
}
\tag{13}
\]

右侧可与 1 取最小值；\(D_{\rm KL}(r\Vert p_s)\) 在此表示 Bernoulli KL。条件是该分量起点不早于实际攻击且接下来的攻击持续、幅值不小于 \(b_j\)。该式控制在日历时刻 \(k+n\) 仍未报警的概率，不是对“截至 \(k\) 尚未误报”条件化后的自动保证。若需要后者，应明确条件化并重新界定。

这是发送机会下界替代逐拍 \(I_{\min}>0\) 的具体方式。仅给出期望增长并不能代替式(13)的高概率分析。

## 7. S1/U1 三档幅值常数及工程含义

使用原有量化半步长：S1 为 0.011628232298833967，U1 为 0.022259755314928388。所有下界均由上述公式直接计算；积分和网格只作独立数值检查。

| 模型 | \(b\) | 发送后 \(|D_t|\) 下界 | \(\epsilon_b\) 下界 | \(I_b\) 下界 | \(p_sI_b\) |
|---|---:|---:|---:|---:|---:|
| S1 | 0.05 | 0.0158167 | 7.48716e-5 | 1.55192e-8 | 3.19260e-9 |
| S1 | 0.10 | 0.0316334 | 2.99391e-4 | 2.47987e-7 | 5.10157e-8 |
| S1 | 0.25 | 0.0790836 | 1.86703e-3 | 9.60022e-6 | 1.97495e-6 |
| U1 | 0.05 | 0.0204592 | 1.80389e-4 | 8.36522e-8 | 1.90560e-8 |
| U1 | 0.10 | 0.0409183 | 7.20972e-4 | 1.33452e-6 | 3.04004e-7 |
| U1 | 0.25 | 0.102296 | 4.48060e-3 | 5.10822e-5 | 1.16365e-5 |

\(p_sI_b\) 是把发送机会再平均后的保守每动作信息保证，不是每拍几乎处处的信息下界。所有六组的逐拍几乎处处正下界仍为零。

例如 \(\alpha=.01\)、动作起点 \(k=50\)、\(w_k=1/(51\cdot52)\)、\(\pi_j=1/3\) 时，\(H_{k,j}\approx13.59\)。即使最强档，2048 拍中 \(2048p_sI_b\) 也仅约 0.00404（S1）或 0.02383（U1）。所以当前保守充分界不能证明目标时域的工程功效。**这不构成实际检测困难的必要下界，也不能据此宣称仿真必然失败。** 实际历史累积偏差可能远大于本文件仅用一次发送注入得到的下界。

弱幅值下 \(\epsilon_b=\Theta(b^2)\)、\(I_b=\Theta(b^4)\)；改变检测器形式没有消除这一保守信息尺度。后续应对比门控候选、基于已观察事件串递推候选偏差的模型候选和既有基线，并分别声明理论适用范围。

## 8. 旧停止能量界不能直接替换停止时刻

原 \((h+1)/\kappa\) 结论使用 \(S_n=\sum(\nu_t-Y_{t+1})\) 的首次越阈时刻 \(\tau_h\)。证明的关键路径界是 \(S_{\tau_h\wedge N}<h+1\)。

若换为混合似然比的首次越阈时刻 \(\tau_\alpha\)，\(S_{\tau_\alpha\wedge N}\) 没有同一个上界，所以附件“定理 C”原样写出的

\[
\mathbb E\sum_{t<\tau_\alpha\wedge N}D_t^2
\le(h+1)/\kappa
\]

没有依据。可以保留原统计量作为单独安全监视器，并分配误报预算后使用两个停止时刻的最小值；或重新从对数似然漂移、偏差传播及停止时刻性质推导新的界。两者都不能被描述为旧界直接迁移。

旧界不能迁移的结论不排除重新证明：[02_mixture_detector_theorems.md](02_mixture_detector_theorems.md) 已另从单侧似然漂移、混合组件的停止上界和发送后静默几何尾推导式(16)–(18)的新偏差能量界；它的右端不同，适用条件也更强。本文件不将它写成旧 \((h+1)/\kappa\) 界，也不声明完整 MSE 恢复界。

## 9. 复算与验证范围

- [compute_information_constants.py](compute_information_constants.py) 与 [constants.json](constants.json)：冻结的原确定性证据，仅 Python 标准库，不访问旧结果、不调用随机数。原有概率偏移与 KL 下界适用于实装候选，但其中的对数区间字段只适用于固定最小偏移对照候选。
- [compute_actual_candidate_constants.py](compute_actual_candidate_constants.py) 与 [constants_actual_candidate.json](constants_actual_candidate.json)：独立补充，加入实装候选正负对数因子及区间界，并显式标记固定最小偏移候选字段。没有改动冻结性能输入或重跑性能试验。
- [deterministic_correction.json](deterministic_correction.json)：记录并发补充发生于冻结之后、原确定性文件精确恢复、补充版本及全部冻结性能输入的哈希检查。
- 确定性检查包括 Riccati 不动点/上端不变性、六档候选概率合法性、101 个方差点上的核差检查、512/1024 区间配对 Simpson 复算、101 个基准概率点上的 KL 检查，以及对应实际 \(K\) 的候选概率偏移与正负对数因子范围。

这些网格检查不是连续参数域的机器形式化证明；连续域保证来自本文件的解析不等式。没有以网格最小值冒充已认证的全局下界。
