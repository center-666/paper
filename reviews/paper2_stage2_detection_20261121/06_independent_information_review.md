# 事件信息上界的独立解析审查

日期：2026-11-21。审查对象是最新 [04_information_upper_bound.md](04_information_upper_bound.md)、[information_upper_bounds.py](information_upper_bounds.py) 及其与冻结模型、事件生成和统计接口的对应关系。本次只读上述文件，仅新增本审查记录；未运行随机抽样，也未重算或改写上界常数和冻结性能输入。

**审查结论：在本轮已声明的固定同向幅值、发送后注入、完整周期独立后置相位、攻击前正确健康初始化和规定事件记录条件下，更紧的 Bernoulli KL 包络、事件链式 KL、随机起点增广及存活条件功效上界均成立。没有发现需要撤回 04 号文档主要解析结论的错误。** S1 强档的约 62.59% 无条件上界与除以 0.99 后的约 63.23% 条件上界，可以用于排除当前事件记录在 2048 拍、1% 误报预算下达到 80% 检出率的目标；不能据此限制读取额外载荷、相位或码字的检测器。

## 1. 审查版本与范围

读取时的 SHA-256 为：

| 文件 | SHA-256 |
|---|---|
| `04_information_upper_bound.md` | `63bce0572b9662a1d1026644d8e036ff551606c0c364fc168cab97165a10cb8d` |
| `information_upper_bounds.py` | `fdbb14a52efd5da0d01b60ce15c21db4eebdfa39d66d09c63752831b6c2cfc48` |
| `information_upper_constants.json` | `06d5b78fe0a1e86a738388a8a683c52d56d9217c2eecc94bae0cbe72b189227b` |
| `protocol.json` | `507dbd465b50b1ca01c5286a2c46925417e5f8303535f07bce2fe65dec751090` |

这些哈希与 [supplementary_analysis_plan.json](supplementary_analysis_plan.json) 中记录的相应版本一致。本审查没有把后补分析称为原附件中的预注册指标。脚本中的网格验证也没有被本审查当作连续域证明；下文直接核对解析不等式。

## 2. 全历史偏差不变区间正确

对本轮实际攻击 \(a_t=b\gamma_t\mathbf 1_{t\ge t_0}\)、\(A>0\)、攻击前 \(D_{t_0-1}=0\)，令 \(B_t=-D_t\)。代码和已核查的分析递推均为

\[
B_t=A(1-K_{\gamma_t})B_{t-1}+\gamma_tK_1b\ge0.
\]

由 Riccati 不变区间得到 \(K_1\in[k_-,k_+]\)。若 \(1-A(1-k_-)>0\)，因为分母随 \(K\) 增大而增大，所有允许发送增益的分母都为正。令

\[
c_B=\max_{K\in[k_-,k_+]}\frac K{1-A+AK},\qquad B_*=bc_B.
\]

对任意 \(B_{t-1}\in[0,B_*]\)，

\[
A(1-K)B_{t-1}+Kb
\le A(1-K)B_*+[1-A(1-K)]B_*=B_*.
\]

静默时 \(B_t\le\rho_0B_{t-1}\le B_*\)，所以 \([0,B_*]\) 在两种更新下都不变。零初值属于该区间，归纳覆盖所有事件历史。这里使用的是发送收缩和注入增益的联合关系，不能把两者分别取最坏值再声称得到了同一个更紧区间。

端点优化也正确：

\[
\frac{d}{dK}\frac K{1-A+AK}=\frac{1-A}{(1-A+AK)^2}.
\]

因此 S1 的 \(A<1\) 在 \(k_+\) 取最大值；U1 的 \(A>1\) 在 \(k_-\) 取最大值。`analytic_bounds` 中 `extremal_k = k_hi if A <= 1 else k_lo`、分母正性检查和发送端点检查与该证明一致。\(A=1\) 时比值恒为 1，任取端点也正确。

所用 \(p_-=p_*(R)\)、\(p_+=\max(P_0,p_*(R+Z^{-1}))\) 对两模型有效，因为 \(P_0\ge p_-\)，两种 Riccati 映射单调且发送映射不大于静默映射。对任意当前事件，后验方差满足

\[
Rk_-\le P_t^+\le\frac{p_+(R+Z^{-1})}{p_++R+Z^{-1}}.
\]

下端取发送更新、上端取静默更新，故 helper 的 `V_lo`、`V_hi` 的确覆盖**所有事件**，不是仅发送时的区间。S1/U1 的 \(\rho_0<1\) 与发送分母正性均已在固定模型下满足。

该区间要求初始分析偏差落在 \([0,B_*]\)，本轮由攻击前正确健康运行给出零初值。若有攻击前遗留偏差、反向注入、载荷相关可变幅值或模型不匹配，应重建不变区间；当前常数不能无条件沿用。

## 3. 核比下界到更紧 KL 包络的每一步均成立

对称量化误差配对给

\[
\frac{F_{\delta,V}(d)}{F_{\delta,V}(0)}
=e^{-d^2/(2V)}
\frac{\int_0^\delta e^{-u^2/(2V)}\cosh(du/V)\,du}
{\int_0^\delta e^{-u^2/(2V)}\,du}
\ge e^{-d^2/(2V)}.
\]

又因 \(F\) 在零点取得全局最大值，且 \(|d|=AB_t\le AB_*\)、\(V\ge V_-\)，有

\[
r_b\nu_t\le p_t^a\le\nu_t,\qquad
r_b=e^{-(AB_*)^2/(2V_-)}.
\]

健康概率 \(\nu_t=s(P_t^+)F(0)\le1/\sqrt{ZV_-}=\nu_+<1\)。这里省去 \(F(0)\le1\) 只放松上界；核比中的 \(F(0)\) 已经正确抵消，没有丢失归一化因子。

固定 \(v\in(0,1)\)，\(\operatorname{kl}(p\Vert v)\) 对 \(p\) 的导数为

\[
\log\frac{p(1-v)}{v(1-p)},
\]

所以在 \(p\le v\) 上单调不增。由 \(p_t^a\ge r_b\nu_t\)，

\[
\operatorname{kl}(p_t^a\Vert\nu_t)
\le\operatorname{kl}(r_b\nu_t\Vert\nu_t).
\]

再固定 \(r=r_b\)，令 \(g(v)=\operatorname{kl}(rv\Vert v)\)。两个 Bernoulli 概率向量
\((rv,1-rv)\) 与 \((v,1-v)\) 都随 \(v\) 仿射变化，所以 KL 的联合凸性确实给出 \(g\) 关于 \(v\) 的凸性。在端点 \(v=0\) 使用连续扩展，两个分布相同，\(g(0)=0\)。非负性给 \(g(v)\ge0\)。因此对 \(0<u<v<1\)，

\[
g(u)\le\frac uv g(v)+\left(1-\frac uv\right)g(0)
=\frac uv g(v)\le g(v).
\]

这严格证明了所需非减性。不能只从“凸”单独推出非减；04 号文档实际使用了额外的 \(g(0)=0\) 和非负性，论证是完整的。由此得到

\[
\boxed{\operatorname{kl}(p_t^a\Vert\nu_t)
\le\operatorname{kl}(r_b\nu_+\Vert\nu_+)=U_b.}
\]

`info_upper` 的两项 `log1p` 正好实现 \(p\log(p/\nu)+(1-p)\log[(1-p)/(1-\nu)]\)，其中 \(p=r_b\nu_+\)。KL 到卡方散度的标准上界则给 \(U_b\le U_b^\chi\)，方向正确。更紧包络没有借助小偏差展开或数值网格极值。

## 4. 链式 KL 的记录范围和时序正确

这里最关键的额外条件是：**给定固定 \(b,t_0\)，\(D_t\) 与 \(P_t^\pm\) 都是事件前缀的确定性函数。** 前者来自固定幅值递推，后者来自 Riccati 递推。虽然接收估计和真实条件均值还依赖已发送连续量测，新的完整周期相位平均消除了它们的绝对位置，只留下 \(D_t,P_t^+\)。

令事件滤过为 \(\mathcal E_t=\sigma(\gamma_0,\ldots,\gamma_t)\)。扩充历史 \(\mathcal G_t\) 下已有
\(\mathbb E_\pi[Y_{t+1}\mid\mathcal G_t]=s(P_t^+)F(AD_t)\)，且右端是 \(\mathcal E_t\)-可测，因此塔式法则给

\[
\mathbb E_\pi[Y_{t+1}\mid\mathcal E_t]
=s(P_t^+)F(AD_t)=p_t^a.
\]

健康模型在相同事件前缀下的条件概率为 \(\nu_t\)，因为其分析偏差始终为零。所有这些条件概率都严格位于 \((0,1)\)，两种有限事件记录具有相同支持，可以直接应用 KL 链式法则。

当前攻击先看到真实事件 \(\gamma_{t_0}\)，再提交载荷修改。因此 \(\gamma_{0:t_0}\) 的分布与健康完全相同，第一项非零散度来自 \(\gamma_{t_0+1}\)。截至 \(\gamma_{t_0+H}\) 恰有 \(H\) 个攻击后审计事件，故

\[
D_{\rm KL}(\mathcal L_\pi(\gamma_{0:t_0+H})\Vert
\mathcal L_0(\gamma_{0:t_0+H}))
=\mathbb E_\pi\sum_{t=t_0}^{t_0+H-1}
\operatorname{kl}(p_t^a\Vert\nu_t)\le HU_b.
\]

`run_experiment.py` 在观察时刻 `t` 使用上一动作的 `true_p`、`nu_a`，仅当 `(t-1)>=onset` 才累加 `cum_kl`，并在 `t==onset+horizon` 记录。这与上式索引一致。

该等式针对事件串及其确定性标签。对于连续载荷相关的自适应攻击，\(D_t\) 不一定由事件串决定，不能直接把相同表达式称为事件条件核；对于包含相位或码字的记录，事件链式 KL 也不能替代更丰富记录的 KL。04 的边界说明是必要条件，而非可省略的措辞。

## 5. 随机起点增广有效，但得到的是相应平均功效界

本轮 `schedule` 是与物理、事件和相位随机流分开的流，均匀起点在 \(50,\ldots,200\) 中独立选取。在健康对照中也可加入同分布、同样独立的辅助起点 \(T\)，但不据此施加攻击。

对固定 \(H\)，比较增广记录

\[
(T,\gamma_{0:T+H})
\]

时，\(T\) 的边缘分布在两假设下相同，故

\[
D_{\rm KL}(\mathcal L_\pi(T,\gamma_{0:T+H})\Vert
\mathcal L_0(T,\gamma_{0:T+H}))
=\mathbb E_T\mathcal K_H(T)\le HU_b.
\]

算法实际不必知道 \(T\)。把 \(T\) 提供给分析记录只会增加信息，因此该上界仍限制原事件型算法。评价事件 \(\{\tau\le T+H\}\) 可在此增广记录上定义；若采用有限时域误报控制，必须有所有可能的 \(T+H\) 位于已校准时域内。本轮最大值为 \(200+2048=2248\)，与攻击实验 D0/D4 的全局预算一致；D3 的保证本来就是任意时刻的。

对于从随机起点设置的独立 episode 得到的 \(\mathbb E_T\mathcal K_H(T)\) 上置信界，它限制的是随机起点分布下的平均检出功效，不能解释为每个给定起点条件下的共同样本上界。纯解析 \(HU_b\) 是逐起点统一成立的，所以没有这一限制。自适应选择或依赖未来物理噪声的起点不在当前增广证明中。

## 6. 检出率反解及存活条件的 0.99 分母正确

若报警事件 \(\mathcal A\) 在健康下满足 \(\alpha_0=\Pr_0(\mathcal A)\le\alpha\)，二元数据处理先给

\[
\operatorname{kl}(\beta\Vert\alpha_0)\le\mathcal K,
\qquad\beta=\Pr_\pi(\mathcal A).
\]

在 \(\beta\ge\alpha\) 时，散度关于第二参数的导数为

\[
\frac{\alpha_0-\beta}{\alpha_0(1-\alpha_0)}\le0,
\]

所以用更大的 \(\alpha\) 替换 \(\alpha_0\) 得到更小散度，仍有 \(\operatorname{kl}(\beta\Vert\alpha)\le\mathcal K\)。\(\beta<\alpha\) 时上界自然成立。`binary_power_upper` 在 \([\alpha,1]\) 上对单调分支二分，并在 \(\mathcal K\ge\log(1/\alpha)\) 时返回 1，与这一定义一致。

对存活集合 \(S=\{\tau>t_0\}\)，攻击在 \(\gamma_{t_0}\) 之后才介入，而 \(\tau\le t_0\) 只使用到此时的事件记录。因此

\[
\Pr_\pi(S)=\Pr_0(S)\ge1-\alpha=0.99.
\]

若 \(D=\{t_0<\tau\le t_0+H\}\)，则 \(D\subseteq S\cap\{\tau\le t_0+H\}\)，从而

\[
\Pr_\pi(D\mid S)
=\frac{\Pr_\pi(D)}{\Pr_\pi(S)}
\le\min\left\{1,\frac{\text{无条件功效上界}}{1-\alpha}\right\}.
\]

随机起点时对每个给定 \(T\) 使用相同攻击前同律关系，再平均，也有相同存活概率下界。`analyze.py` 中 `eligible_power_upper = min(1, binary_upper/(1-alpha))` 与这个保守界一致。

这里必须使用已证明、适用于攻击前时域的误报预算，而不是用本次样本中的零误报来代替 \(\alpha\)。若检测器在攻击前做了不同校准、偷偷使用真实起点重置、训练/测试不分或已有未知污染，攻击前同律或健康误报前提可能不再成立。当前冻结协议没有这些更改；D0/D4 仅能在各自预定预算内使用本结论。

## 7. 离线经验 Bernstein 与必要时域的检查

脚本把整个 episode 的累计条件 KL \(X_H\) 视为一个样本。其解析范围 \([0,HU_b]\) 对所有事件历史成立，因此同一轨迹内的时序相关不妨碍跨 episode 的独立样本界。

helper 使用分母 \(m-1\) 的样本方差，以及

\[
\sqrt{2\widehat V\log(2/\delta_c)/m}
+\frac{7L_H\log(2/\delta_c)}{3(m-1)},
\]

与标准 Maurer–Pontil 型单侧有界经验 Bernstein 形式一致。再与确定的解析上界 \(L_H\) 取最小值，仍是上置信界。72 格各分配 \(0.05/72\) 后用并合界，不要求三个相邻时域相互独立。需要的是每格 episode 按声明模型独立生成，以及最终样本没有参与候选或阈值调整。

这里的统计保证仍是理想模型和正确抽样下的数学结论；浮点累计、CDF 差分及方差相减没有使用定向舍入，因此不能额外包装成机器认证的数值区间。04 已区分数值显示与解析证明，无须更改主要结论。

由于 \(1-e^{-\eta_b}\le\eta_b\) 且 \(B_*=c_Bb\)，\(U_b\le U_b^\chi\le C_{\rm model}b^4\) 成立。结合功效上界得到的 \(b^{-4}\) 时域约束方向为**必要条件**，不是充分检测保证。`necessary_horizon_exact_kernel_bound_binary_data_processing` 使用更小的 \(U_b\) 作为分母，因而给出更强的必要条件，方向正确。

## 8. 可保留结论与必须保留的边界

本次审查支持保留：更紧的偏差不变区间、Bernoulli 凸性包络、规定事件记录的全历史 KL 上界、随机起点平均信息界、以及正确处理存活条件后的检测功效上界。S1 \(b=0.25,H=2048\) 的显示值为

\[
\mathcal K_H\le2.225161369\ldots,\qquad
\Pr_\pi(\text{截至终点报警})\le0.6259249099\ldots,
\]

所以存活条件检出率至多为 \(0.6259249099/0.99\approx0.632247\)，仍严格低于 0.8。这个结论来自解析上界，不依赖某一次检测实验失败。

结论须始终限定于本轮固定幅值、固定或独立随机起点、正确健康先验/滤波模型、事件串及确定性协方差标签。改变记录、主动探测协议、认证信息、攻击前污染或物理闭环关系后，需要重新建立相应信息上界；本审查没有否定这些后续工程路线。
