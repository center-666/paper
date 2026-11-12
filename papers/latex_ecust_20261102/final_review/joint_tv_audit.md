# 定理 3.2 匹配下界：联合日志、二阶导数与 TV 常数独立审计

审计日期：2026-10-20。

审计对象为 `latex_clarity_20261020/theory.tex`、`main_joint_kernel.tex` 和 `vector_proof.tex`。下述行号对应本次读取的上述源文件，未改动稿件。审计依据是模型与逐式推导，不以代码运行、旧版检查结论或数值实验代替证明。

## 1. 结论与适用范围

**没有发现推翻定理 3.2 匹配下界的数学错误。** 在稿件的全状态含噪观测、可信实际预测反馈、可信事件位、发送后载荷攻击以及固定有限时刻等条件下，两拍公平符号攻击具有合法因果实现；其目标时刻损伤为 \(L_v\eta^2\)，完整日志 TV 不超过 \(C_\pm\eta^2\)。所用

\[
C_\pm=\frac14\sum_h w_h B_h
\]

的系数正确。

本结论为独立数学审阅，**不是机器形式化证明**，也不证明论文整体的新颖性、全部附录或工程协议适用性。为提高可核查性，建议对附录 B 的共同测度、平移可微性和一致常数补充三处短说明；不需要改动主定理、攻击构造或现有常数。

## 2. 模型与条件分布的前提

位置：`theory.tex` 第 4–59、61–77 行；`vector_proof.tex` 第 13–30、54–77 行。

给定目标时刻前完整无攻击记录，接收端预测等于真实条件均值。令其均值为 \(m_k^-\)，令事件前缀为 \(h\)，则

\[
u=y_k-m_k^-\sim N(0,S_h),\qquad S_h=P_k^-(h)+R.
\]

当前发送概率为 \(1-g(u)\)，因此**未归一化**发送密度是

\[
f_h(u)=\phi_{S_h}(u)[1-g(u)]
      =\phi_{S_h}(u)-s_h\phi_{T_h}(u),
\quad \int f_h=p_h=1-s_h.
\]

\(S_h,T_h,S'_h\) 均正定，\(p_h\in(0,1)\)，所有有限事件前缀的权重 \(w_h>0\)。此处不应将 \(f_h\) 再除以 \(p_h\)，因为联合核已经包括当前发送分支的概率。正文和附录均未多除或漏乘 \(p_h\)。

给定当前真实测量 \(u\) 和发送事件后，事件似然只依赖已知 \(u\)，对状态的高斯后验不再提供额外信息。于是

\[
\mu_{k+1}^-=A(m_k^-+K_hu),\qquad
e=y_{k+1}-\mu_{k+1}^-\sim N(0,S'_h).
\]

这一条件分布不随 \(u\) 改变，因而 \(e\) 与 \(u\) 在给定前史、当前发送事件后条件独立。注意独立的是按真实条件均值居中的 \(e\)，不是原始 \(y_{k+1}\) 与当前测量。

## 3. 两拍动作与联合核正确

位置：`theory.tex` 第 247–265 行；`main_joint_kernel.tex` 第 3–23 行；`vector_proof.tex` 第 72–108 行。

将有符号幅值记为 \(t\)。当前发送后注入 \(tv\)，接收创新

\[
z=u+tv,\qquad
D_k=-tK_hv,\qquad d_{k+1}=-tu_h,\quad u_h=AK_hv.
\]

下一拍原始触发创新为 \(e-tu_h\)。若发送，注入补偿 \(tu_h\)，接收创新恰为 \(e\)。这给出

\[
\begin{aligned}
\mathcal K_{h,-tu_h}(\{\bot\})
 &=\int\phi_{S'_h}(e)g(e-tu_h)\,de,\\
\mathcal K_{h,-tu_h}(de)
 &=\phi_{S'_h}(e)[1-g(e-tu_h)]\,de,\\
F_h(t)(dz,d\xi)
 &=f_h(z-tv)\,dz\,\mathcal K_{h,-tu_h}(d\xi).
\end{aligned}
\]

\(\mathcal K\) 质量为 1；\(F_h(t)\) 质量始终为 \(p_h\)。下一拍补偿符号与正文一致。若将其误取为 \(-tu_h\)，上述核便不成立。

两个动作的范数分别为 \(|t|\) 和 \(|t|\|u_h\|_2\)。选择 \(\eta=\kappa b\) 及稿件中的 \(\kappa\)，在 \(t=\pm\eta\) 时均满足峰值约束。动作只需事件前缀、私有符号和已知模型，不读取未发送测量或未来噪声。

下一发送分支仍有 \(D_{k+1}=-tu_h=d_{k+1}\)，因此稿件将补偿解释为“接收创新的平移补偿”正确，不能称为估计偏差恢复。

## 4. 共同支配测度与二阶 \(L^1\) 可微性

位置：`main_joint_kernel.tex` 第 25–44 行；`vector_proof.tex` 第 110–144 行。

### 4.1 将原子和连续部分写成同一密度

令 \(\nu=\delta_\bot+\lambda_n\) 为 \(\{\bot\}\sqcup\mathbb R^n\) 上的测度，定义

\[
\begin{aligned}
q_{h,t}(\bot)&=\int\phi_{S'_h}(e)g(e-tu_h)\,de,\\
q_{h,t}(\xi)&=\phi_{S'_h}(\xi)[1-g(\xi-tu_h)],
\qquad \xi\in\mathbb R^n.
\end{aligned}
\]

则 \(q_{h,t}\) 是 \(\mathcal K_{h,-tu_h}\) 对 \(\nu\) 的密度，而 \(F_h(t)\) 对固定测度 \(\lambda_n\otimes\nu\) 的密度为

\[
\rho_{h,t}(z,\xi)=f_h(z-tv)q_{h,t}(\xi).
\]

该支配测度不依赖 \(t\)、私有符号或攻击策略。完整日志本身含有确定性反馈关系，不一定对一个普通欧氏空间的 Lebesgue 测度有密度；证明不需要这样的结论，因为它先在上述坐标空间工作，再作固定映射。

### 4.2 核的导数与连续性

记 \(a_h=u_h^\top Zu_h\)。对任意 \(x\)，

\[
\partial_{u_h}g(x)=-(u_h^\top Zx)g(x),\qquad
\partial_{u_h}^2g(x)=\big[(u_h^\top Zx)^2-a_h\big]g(x).
\]

由 Cauchy–Schwarz 及一维最大值得

\[
\|\partial_{u_h}g\|_\infty\le\sqrt{a_h/\mathrm e},
\qquad
\|\partial_{u_h}^2g\|_\infty\le a_h.
\]

连续部分关于 \(t\) 的导数为

\[
q'_{h,t}(\xi)=\phi_{S'_h}(\xi)\partial_{u_h}g(\xi-tu_h),
\qquad
q''_{h,t}(\xi)=-\phi_{S'_h}(\xi)\partial_{u_h}^2g(\xi-tu_h).
\]

原子部分则为

\[
q'_{h,t}(\bot)=-\int\phi_{S'_h}(e)\partial_{u_h}g(e-tu_h)\,de,
\quad
q''_{h,t}(\bot)=\int\phi_{S'_h}(e)\partial_{u_h}^2g(e-tu_h)\,de.
\]

因此一阶、二阶导数在连续部分分别由
\(\sqrt{a_h/\mathrm e}\,\phi_{S'_h}\)、\(a_h\phi_{S'_h}\) 支配，原子处由相应常数支配。将原子和连续部分合并，得到可积支配函数
\[
\sqrt{a_h/\mathrm e}\,[\mathbf1_{\{\bot\}}+
\phi_{S'_h}\mathbf1_{\mathbb R^n}],
\qquad
a_h[\mathbf1_{\{\bot\}}+\phi_{S'_h}\mathbf1_{\mathbb R^n}].
\]

支配收敛及微积分基本定理给出 \(q_{h,\cdot}\in C^2(\mathbb R;L^1(\nu))\)，并且

\[
\sup_{t\in\mathbb R}\|q'_{h,t}\|_1\le2\sqrt{a_h/\mathrm e}=l_1(u_h),
\qquad
\sup_{t\in\mathbb R}\|q''_{h,t}\|_1\le2a_h=l_2(u_h).
\]

这里的 2 来自原子与连续密度两部分，不能省略。

### 4.3 平移密度与乘积核

\(f_h\) 是两个高斯密度的线性组合，属于 \(W^{2,1}(\mathbb R^n)\)。令 \(f_{h,t}(z)=f_h(z-tv)\)，则平移在 \(L^1\) 中连续，且

\[
\frac{d}{dt}f_{h,t}=-\partial_v f_h(\cdot-tv),\qquad
\frac{d^2}{dt^2}f_{h,t}=\partial_v^2 f_h(\cdot-tv).
\]

因此 \(t\mapsto f_{h,t}\) 是二阶连续 \(L^1\) 可微的。严格依据是可积弱导数、平移连续性以及
\(f_{h,t+s}-f_{h,t}=-\int_0^s\partial_v f_h(\cdot-(t+r)v)\,dr\)；
**不需要所有实数平移共同被同一个可积点态函数支配**。

张量乘积 \(L^1(\lambda_n)\times L^1(\nu)\to L^1(\lambda_n\otimes\nu)\) 是连续双线性映射，因为
\(\|f\otimes q\|_1=\|f\|_1\|q\|_1\)。故乘积求导合法：

\[
\rho''_{h,t}
=f''_{h,t}\otimes q_{h,t}
+2f'_{h,t}\otimes q'_{h,t}
+f_{h,t}\otimes q''_{h,t}.
\]

利用 \(\|q_{h,t}\|_1=1\)、\(\|f_{h,t}\|_1=p_h\)，有

\[
\sup_{t\in\mathbb R}\|F_h''(t)\|_{\rm var}
\le F_{2,h}+2F_{1,h}l_1(u_h)+p_hl_2(u_h)=B_h.
\]

高斯导数估计
\(\|\partial_v\phi_\Sigma\|_1=\sqrt{2/\pi}\sqrt{v^\top\Sigma^{-1}v}\)、
\(\|\partial_v^2\phi_\Sigma\|_1\le2v^\top\Sigma^{-1}v\)
给出稿件的 \(F_{1,h},F_{2,h}\)。第二个估计较保守但有效。

### 4.4 一致性

- **对幅值 \(t\)：** 上述界在全部 \(t\in\mathbb R\) 上成立，不仅在某个局部小幅值邻域内成立。
- **对连续载荷前史：** 居中后 \(S_h,S'_h,K_h,p_h\) 只依赖事件前缀；\(B_h\) 不依赖前史载荷的具体实数取值。
- **对事件前缀：** 固定有限 \(k\) 时只有有限个 \(h\)，故 \(\max_h B_h<\infty\)。
- **对 \(b,\varepsilon\)：** \(B_h,C_\pm,\kappa,L_v\) 均不依赖二者。因此下界构造不需要另加“充分小 \(b\)”条件。
- **对维数、时刻、模型：** 不存在已证明的统一常数；本证明只支持稿件所声明的固定维数、固定有限时刻和固定模型。上界中的 \(q\) 另依赖有限参考峰值 \(b_{\rm ref}\)，不能据下界的全实数导数界删除主定理的峰值范围。

## 5. 中心 Taylor 公式与两个 \(1/2\) 因子

位置：`main_joint_kernel.tex` 第 45–63 行；`vector_proof.tex` 第 145–157 行。

由 \(C^2(L^1)\) 性质，Banach 空间内积分余项成立：

\[
Q_h^\eta-F_h(0)
=\frac12\int_0^\eta(\eta-t)
[F_h''(t)+F_h''(-t)]\,dt.
\]

所以

\[
\|Q_h^\eta-F_h(0)\|_{\rm var}
\le\frac12(2B_h)\int_0^\eta(\eta-t)\,dt
=\frac12B_h\eta^2.
\]

上式第一个净 \(1/2\) 来自中心平均与积分余项。由于 \(Q_h^\eta\) 与 \(F_h(0)\) 均为质量 \(p_h\) 的正测度，差测度总质量为零，因此按稿件的 \(\sup_E\) 定义，

\[
\sup_E|Q_h^\eta(E)-F_h(0)(E)|
=\frac12\|Q_h^\eta-F_h(0)\|_{\rm var}
\le\frac14B_h\eta^2.
\]

这就是第二个 \(1/2\)。该等式对等质量次概率测度同样有效，无需先归一化。若只用 \(\|\cdot\|_{\rm var}\) 而忘记这一步，得到的常数会变成更保守的 \(1/2\sum_h w_hB_h\)；稿件的 \(1/4\) 没有少乘因子。

## 6. 从两拍核到完整日志

位置：`main_joint_kernel.tex` 第 56–63 行；`vector_proof.tex` 第 101–108、150–158 行。

对固定完整前史 \(\zeta\)，由 \((z,\xi)\) 构造日志的映射为

\[
\widetilde y_k=m_k^-+z,\quad
m_{k+1}^-=A(m_k^-+K_hz),\quad
\widetilde y_{k+1}=m_{k+1}^-+\xi\quad(\xi\ne\bot).
\]

该映射只依赖已知前史和核坐标，不依赖 \(t\)。当前发送事件固定为 1，下一事件由 \(\xi=\bot\) 与否确定。当前静默分支两拍都无攻击，恰与正常分支一致。

记共同前史分布为 \(\mu_{\rm pre}(d\zeta)\)。差核先对同一 \(\mu_{\rm pre}\) 积分，再经固定映射，故

\[
\begin{aligned}
\Delta_{\rm full}
&\le \int \frac12\|Q_{h(\zeta)}^\eta-F_{h(\zeta)}(0)\|_{\rm var}
\,\mu_{\rm pre}(d\zeta)\\
&\le\frac{\eta^2}{4}\int B_{h(\zeta)}\,\mu_{\rm pre}(d\zeta)
=\frac{\eta^2}{4}\sum_h w_hB_h.
\end{aligned}
\]

这一步没有忽略连续前史，也没有将共享私有符号的两拍边缘分布误当作独立分布。

## 7. 损伤与私有混合

位置：`theory.tex` 第 260–276 行；`vector_proof.tex` 第 76–77、159–161 行。

目标时刻的事件产生在攻击之前，协方差分布不变。发送时偏差为 \(-\sigma\eta K_hv\)，静默时为零，故
\[
J_k=L_v\eta^2,\qquad L_v=\sum_h w_hp_h\|K_hv\|_2^2>0.
\]

在开始前以独立私有概率
\(\lambda=\min\{1,\varepsilon/(C_\pm\kappa^2b^2)\}\)
选择整段攻击策略，否则选择零动作，联合分布是两个完整运行分布的混合。与正常分布的差及目标损伤均精确乘以 \(\lambda\)，从而

\[
\Delta_{\rm full}\le\varepsilon,\qquad
J_k=L_v\min\{\kappa^2b^2,\varepsilon/C_\pm\}
\ge L_v\min\{\kappa^2,C_\pm^{-1}\}\min\{b^2,\varepsilon\}.
\]

通过记录映射的数据处理性质，同一攻击同时满足事件串、精确标记记录的预算。\(k=0\) 取唯一空前缀；\(\varepsilon=0\) 选择零动作，均无端点缺口。

## 8. 建议修订：只补足可核查的说明

1. **附录第 125–127 行：** 将“核导数由常数倍的高斯密度支配”限定为连续部分，并补上原子处由常数支配。可写成：“以 \(\nu=\delta_\bot+\lambda_n\) 为共同测度，其一、二阶导数分别由 \(\sqrt{a_h/\mathrm e}(\mathbf1_{\{\bot\}}+\phi_{S'_h})\)、\(a_h(\mathbf1_{\{\bot\}}+\phi_{S'_h})\) 支配；这里高斯密度延拓为在原子处取零。”这样涵盖原子且不含歧义。
2. **附录第 141–144 行：** 补一句“\(f_h\in W^{2,1}\)，平移在 \(L^1\) 中连续；张量乘积为连续双线性映射，故乘积核属于 \(C^2(\mathbb R;L^1)\)”。这比对平移直接笼统引用高斯支配更准确。
3. **附录常数之后或正文第 43 行：** 明确“\(\sup_{t\in\mathbb R}\|F_h''(t)\|_{\rm var}\le B_h\)，且该常数与给定事件前缀下的连续载荷前史无关”。这正面回答读者对一致性的疑问，不改变任何假设。
4. **可选一行：** 在得到 \(C_\pm\) 前加入第 6 节中的前史积分式，使 \(w_h\) 从何而来以及为何没有漏掉载荷历史一目了然。

这些是说明增强，不是对错误定理的补救。此次审计范围内没有需要撤回的公式或数值常数；仍应由其他审阅分别核查上界及条件高斯性的一般策略范围、记录删减反例、数值证书和近邻文献差异。

## 9. 可直接用于附录 B.3 的精简 LaTeX

下段可替换第 125–127 行，并替代第 142–143 行重复的可微性说明。原有高斯导数估计、\(F_{1,h},F_{2,h},B_h\) 公式及 Taylor 公式保留。建议放在定义 \(B_h\) 后，这样显示式中的 \(B_h\) 已有定义。未新增数学主张，仅将原有函数分析步骤具体化。

```latex
令 $\nu=\delta_\bot+\lambda_n$，其中 $\lambda_n$ 为连续部分的 Lebesgue 测度，
并以 $q_{h,t}$ 表示 $\mathcal K_{h,-tu_h}$ 关于 $\nu$ 的密度。
记 $a_h=u_h^\top Zu_h$。连续部分的一、二阶 $t$ 导数分别由
$\sqrt{a_h/\mathrm e}\,\phi_{S'_h}$ 和 $a_h\phi_{S'_h}$ 支配，
原子处的相应导数绝对值则分别不超过 $\sqrt{a_h/\mathrm e}$ 和 $a_h$。
由支配收敛定理，$t\mapsto q_{h,t}$ 属于 $C^2(\mathbb R;L^1(\nu))$。
另一方面，$f_h$ 是两个高斯密度的线性组合，属于 $W^{2,1}(\mathbb R^n)$；
平移在 $L^1$ 中连续，故 $t\mapsto f_h(\cdot-tv)$ 二阶连续 $L^1$ 可微。
张量乘积为连续双线性映射，因此联合密度
$f_h(z-tv)q_{h,t}(\xi)$ 关于 $t$ 同样二阶连续 $L^1$ 可微，且
\begin{equation}
 \sup_{t\in\mathbb R}\|F_h''(t)\|_{\rm var}
 \le F_{2,h}+2F_{1,h}l_1(u_h)+p_hl_2(u_h)=B_h.
\end{equation}
该界不依赖连续载荷前史或有符号幅值 $t$；固定有限时刻下事件前缀只有有限个，
因而所有前缀的常数均有限。
```

编辑说明：上述高斯支配只用于 \(q_{h,t}\)，其高斯因子 \(\phi_{S'_h}\) 未平移；当前密度 \(f_h(\cdot-tv)\) 的 \(C^2(L^1)\) 性质由平移连续性证明。若另用支配收敛直接处理后者，只能在任意固定 \(t\) 的紧邻域构造可积包络，不能声称全部 \(t\in\mathbb R\) 共享一个可积点态包络；全实数的一致结论是导数的 \(L^1\) 范数界。
