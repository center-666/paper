# 理论可行性、完整推导与不能作为创新的部分

状态：`PROVED/DERIVED`表示本轮完整推导；`STANDARD`表示该推导属于成熟工具，不能据此宣称新定理；`CONDITIONAL`表示只在明确条件下成立；`OPEN`表示实际协议中的关键前提未建立；`DISPROVED`表示原泛化命题存在反例。下文不证明任何新防御已经优于强基线。

## 1. 先区分三个数学对象

1. 健康与受攻状态之间的差分\(\delta\hat x\)是污染传播量，并非真实估计误差\(e=x-\hat x\)。\(\|\delta\hat x\|\)减小不必使MSE减小，因为正常误差与污染有交叉项。
2. 模型内部名义协方差、给定合法信息的真实条件协方差、总体误差二阶矩不是同一对象。攻击偏置有均值时应使用\(S=\mathbb E[\zeta\zeta^T]=P+\mu\mu^T\)，不能只传播P。
3. oracle已知攻击停止、oracle已知当前全网真误差、事后读取未来真状态，是三个不同资源等级。后两者不能作为部署输入。事后oracle只提供能力上限，其收益存在也不构成立项的充分条件。

## 2. T-B1：固定恢复日程下的精确有限窗MSE目标

**状态：PROVED，STANDARD；可作为调度比较的正确模型，但不是论文主创新。**

令\(\tau\)为攻击结束后的恢复起点，\(\zeta_k=\operatorname{col}(e_1(k),\ldots,e_N(k),b^-_{e_1}(k),\ldots,b^-_{e_E}(k))\)，当前维数为30。对每个候选恢复日程\(u\)，收包矩阵为

\[
D_u(k)\zeta_k=\operatorname{col}\big((1-s_j^u(k))b^-_{ji}(k)+s_j^u(k)e_j(k)\big)_{(j,i)}.
\tag{B.3}
\]

由(0.2)—(0.3)装配

\[
\zeta_{k+1}=M_u(k)\zeta_k+G_u(k)\omega_k.\tag{B.4}
\]

**首先固定决策过滤。** 共同问题模型中的\(\mathcal I_i(k)\)包含当前量测\(y_i(k)\)，所以不能据此假设包含\(v_i(k)\)的当前新噪声仍独立、零条件均值。这里专门使用**首个恢复量测尚未进入之前**的\(\mathcal F_{\tau^-}\)：仅包含至tick\(\tau-1\)已可获得的本地量测、实际接收包/时刻，以及由这些历史产生的当前\(\hat x_i(\tau)\)、缓存和已知外生日程。不包含\(y_i(\tau)\)或\(v_i(\tau)\)。协调者若汇集其他节点过去信息，须另计通信，不能当免费本地信息。

**假设B1。** 候选完整恢复日程在\(\tau^-\)时根据\(\mathcal F_{\tau^-}\)确定，之后不读取新量测/未来噪声；恢复窗无新的直接篡改；K和融合权重在每条候选日程下已给定；不存在状态依赖cap/门控，或者其系数已作为\(\mathcal F_{\tau^-}\)可测的固定外部模式给定；\(\omega_k=\operatorname{col}(w_k,v_1(k),\ldots,v_N(k))\)对\(k\ge\tau\)在时间上独立、零均值、具有已知协方差\(\Omega_k\)，并独立于\(\zeta_\tau\)和此前历史。这与当前模型独立新噪声、仅由旧数据产生\(\hat x(\tau)\)的时序一致；攻击前历史可非高斯、可与旧噪声相关，不要求\(\zeta_\tau\)高斯。

如果决策已使用当前innovation\(y_i(\tau)-H_i\hat x_i(\tau)\)，则该定理只能从**下一tick**开始重置初始过滤/误差矩，或者显式增广当前\(v_i(\tau)\)及其条件交叉矩；不能仍在同一tick把它作为零均值独立新噪声。已读当前量测后的检测停止时刻同理，不能在证明中隐去这一拍。现有engine先计算innovation并不妨碍预先固定外生日程的分析，但实际残差自适应调度不能自动继承本定理。

这里的固定\(M_u\)假设**不自动适用于**实际cap、空间门控、残差调度或闭环SoD。对它们应直接模拟完整分支，或作条件转移积分；不能条件于观察到的模式后仍使用未经证明的原健康高斯矩。

给定上述量测前过滤，令\(S_\tau=\mathbb E[\zeta_\tau\zeta_\tau^T\mid\mathcal F_{\tau^-}]\)。下文全部J、S及噪声代价均在同一\(\mathcal F_{\tau^-}\)下取条件期望。由B1独立新噪声与零均值，

\[
S_{k+1}=M_u(k)S_kM_u(k)^T+G_u(k)\Omega_kG_u(k)^T.\tag{B.5}
\]

本式完整保留节点之间、节点与缓存之间、不同缓存之间的交叉相关。过程噪声为同一个真实状态的噪声，进入全部误差块的通道相关，不能对节点复制为独立噪声。

设\(W_\ell\succeq0\)只提取接收者或网络估计误差，\(\ell=1,\ldots,H\)，\(\Phi_u(\ell,0)=M_u(\tau+\ell-1)\cdots M_u(\tau)\)，则

\[
J_u(S_\tau)=\mathbb E\sum_{\ell=1}^H\zeta_{\tau+\ell}^TW_\ell\zeta_{\tau+\ell}
=\operatorname{tr}(P_u S_\tau)+\eta_u,\tag{B.6}
\]
\[
P_u=\sum_{\ell=1}^H\Phi_u(\ell,0)^TW_\ell\Phi_u(\ell,0),\tag{B.7}
\]
\[
\eta_u=\sum_{\ell=1}^H\sum_{r=0}^{\ell-1}
\operatorname{tr}\{W_\ell\Phi_u(\ell,r+1)G_u(\tau+r)\Omega_{\tau+r}
G_u(\tau+r)^T\Phi_u(\ell,r+1)^T\}.\tag{B.8}
\]

其中\(\Phi_u(\ell,r+1)=M_u(\tau+\ell-1)\cdots M_u(\tau+r+1)\)，空乘积为I。

**证明。** 根据B1，条件于\(\mathcal F_{\tau^-}\)后，全部候选的\(M_u,G_u\)为确定矩阵。展开(B.4)得到初值响应加各新噪声响应；B1保证\(\mathbb E[\zeta_\tau\omega_k^T\mid\mathcal F_{\tau^-}]=0\)和\(\mathbb E[\omega_r\omega_k^T\mid\mathcal F_{\tau^-}]=0\)（\(r\ne k\)）。故混合项条件期望为0。将\(\mathbb E[z^TWz\mid\mathcal F]=\operatorname{tr}(W\mathbb E[zz^T\mid\mathcal F])\)逐项相加得到(B.6)—(B.8)。所用工具仅为线性系统变参数公式及trace恒等式。证毕。

**可计算性限制。** oracle可利用已知\(S_\tau\)枚举小预算日程；本地节点不能直接获知全网\(S_\tau\)。把离线完整轨迹算出的S当作线上信息，属于越权。若原攻击历史未知，条件S还依赖未知攻击过程，不能沿用健康P而忽略污染均值。

## 3. T-B2：有害刷新可被排除的有限预算风险证书

**状态：CONDITIONAL / PROVED；标准鲁棒优化结论。实际紧不确定集的构造为OPEN，当前负实验不支持继续开发。**

沿用B1及同一个量测前过滤\(\mathcal F_{\tau^-}\)，有限预算日程集\(\mathcal U_B\)包含被动日程0，且全部满足同一明确字节预算。定义\(\Delta P_u=P_u-P_0\)，\(\Delta\eta_u=\eta_u-\eta_0\)。若从该合法过去信息获得\(\mathcal F_{\tau^-}\)可测的\(\hat S\)及半径\(\delta\ge0\)，并保证

\[
S_\tau\succeq0,\qquad\|S_\tau-\hat S\|_*\le\delta,\tag{B.9}
\]

以及噪声差代价估计误差\(|\Delta\eta_u-\widehat{\Delta\eta}_u|\le\beta_u\)，则对每个u

\[
J_u-J_0\le U_u:=\operatorname{tr}(\Delta P_u\hat S)
+\widehat{\Delta\eta}_u+\delta\|\Delta P_u\|_2+\beta_u.\tag{B.10}
\]

取\(U_0=0\)，在\(\mathcal U_B\)内选\(\hat u\in\arg\min U_u\)，则

\[
J_{\hat u}\le J_0.\tag{B.11}
\]

若\(u^*\)为真实代价最优日程，令\(\varepsilon_u=\delta\|\Delta P_u\|_2+\beta_u\)，则还得到

\[
0\le J_{\hat u}-J_{u^*}\le2\varepsilon_{u^*}
\le2\max_{u\in\mathcal U_B}\varepsilon_u.\tag{B.12}
\]

**证明。** 核范数/谱范数对偶给
\(|\operatorname{tr}(\Delta P_u(S_\tau-\hat S))|\le\|\Delta P_u\|_2\|S_\tau-\hat S\|_*\)。加上噪声代价误差界得(B.10)。由于被动日程可选，\(U_{\hat u}\le U_0=0\)，故(B.11)。再用\(J_{\hat u}-J_0\le U_{\hat u}\le U_{u^*}\le J_{u^*}-J_0+2\varepsilon_{u^*}\)得(B.12)。证毕。

**不是何种保证。** 这不证明额外通信一定有收益；保守不确定集可使最优动作始终为0。它也不是路径上每次真实误差都下降，而是给定正确条件矩集合下的期望有限窗代价保证。若(B.9)仅以概率\(1-\alpha\)成立，结论仅在同一覆盖事件上成立；不能未经额外有界性推成无条件MSE无劣化。多次在线重规划还需同时覆盖/递推条件校准。

**可能的方法增量在哪里。** 仅当合法局部缓存与量测能给出足够紧且低成本的(B.9)，并在相同额外字节下优于周期/随机/标准VoI，才值得研究“污染感知刷新”。目前没有该能力，也没有收益门槛支持；不能把(B.10)这项标准上界本身作为新方法。

## 4. B的反例：额外真实发送并不单调改善恢复

**状态：DISPROVED，完整解析反例。**

在无噪声的一拍Yang特例中，若新包将缓存误差\(b_{ji}^-\)换成sender误差\(e_j\)，其他项相同，则

\[
e_i^{\rm new,+}=e_i^{\rm passive,+}+\epsilon A(e_j-b_{ji}^-).\tag{B.13}
\]

故一拍真实风险差为

\[
\Delta J=2\epsilon\mathbb E[(e_i^{\rm passive,+})^TWA(e_j-b_{ji}^-)]
+\epsilon^2\mathbb E\|A(e_j-b_{ji}^-)\|_W^2.\tag{B.14}
\]

取标量\(A=1,\epsilon=.2,e_i^{\rm passive,+}=0,b_{ji}^-=0,e_j=1,W=1\)，被动MSE为0，额外发送后为0.04。该新包是sender真实当前估计，不涉及新的攻击输入。它是合法的一拍增广误差状态，未声称恰由某个G2指定seed到达；足以否定“任意历史污染状态下真实新包均有利”的全称结论。

因此恢复效益不对额外发送集合单调，不能未经证明直接使用monotone-submodular贪心的\(1-1/e\)保证；只使数据更新鲜也不能代替真实MSE目标。等预算最优应允许0动作；强制正好使用全部预算可能比被动更差。

## 5. T-C：重接入时的含交叉项风险证书

**状态：PROVED，STANDARD；关键统计输入OPEN。**

考虑给定实际信息\(\mathcal I_i\)后，固定当前包及后续模式的一拍重接入。误差写为\(a+\gamma b\)，\(0\le\gamma\le1\)。令

\[
\ell=\mathbb E[a^TWb\mid\mathcal I_i],\quad
q=\mathbb E[b^TWb\mid\mathcal I_i]\ge0.
\]

展开平方即得(C.1)，若\(q>0\)已知，最优\(\gamma^*=\operatorname{clip}_{[0,1]}(-\ell/q)\)。若仅有\(\ell\le\bar\ell<0\)、\(q\le\bar q>0\)，对\(0<\gamma\le\min\{1,-2\bar\ell/\bar q\}\)，

\[
J(\gamma)-J(0)\le2\gamma\bar\ell+\gamma^2\bar q\le0.\tag{C.2}
\]

若\(q=0\)，则\(W^{1/2}b=0\)几乎必然，\(\ell=0\)，融合对该目标无影响。不能让零分母生成无限“最优权重”。若\(\bar\ell\ge0\)，从此上界得不到任何严格正重接入权重的无劣化保证。

**证明工具。** 条件二阶矩展开、凸二次最小化，无新理论。它说明“估计攻击幅值更准”“权重随信任恢复”均不能自动保证MSE改善；\(\ell\)的符号和交叉相关决定恢复价值。只保存残差平方或攻击概率不足以一般性决定该符号。

**为何当前不立项。** 算出\(\ell,q\)需要当前包、正常误差和污染的联合条件统计，不能使用真状态或健康反事实。无独立可辨识证据时，区间可能只能允许\(\gamma=0\)。Nasiri/Gao的直接方法是否已能完成同一风险权重必须先排重。

## 6. A：信息价值不能单独给出稳定性定理

**CONDITIONAL。** 若方向权重方案对其所有允许缓存/融合模式满足共同Lyapunov不等式

\[
M_\sigma^TPM_\sigma-P\preceq-Q_0,\quad P\succ0,Q_0\succ0,\tag{A.2}
\]

且噪声二阶矩有界，则由标准随机Lyapunov递推得到均方最终有界。对有限周期日程，也可用周期Lyapunov或lifted transition代替共同P。

**OPEN。** 当前名义K、部分观测H、稀疏缓存、门控和方向矩阵是否满足(A.2)，未建立。只证明\(\operatorname{rank}\mathcal O=2\)或保留不可观方向，不足以推出(A.2)。让所有节点重新变成局部可检测后证明稳定，也不能替代原G3问题。

**标准/新意边界。** (A.2)及其噪声界是标准；潜在增量只能来自方向机制在同误拒绝/通信风险下保留了有用信息，且能给出与实际缓存模式有关的可计算证书。G3未通过前不实现该机制。

## 7. D：事件一致性检查的保证与两个反例

**T-D（PROVED，STANDARD）。** 无丢包、发送阈值公开、上次真实发送载荷已知、当前不是超时的条件下，健康新包必满足(D.2)。因此拒绝不满足(D.2)的值，在这些假设下无误拒绝。证明即发送规则本身；不能包装成新检测定理。

**DISPROVED：满足发送事件不意味着没有Replay。** 标量真实发送参考0、当前2、阈值1、历史包−2；真实包与Replay均在触发集合\(\{|z|>1\}\)，事件检查无法区分。该反例也说明已有触发事件只有一个粗粒度约束，不等于新鲜度认证。

**DISPROVED：接收参考可以无条件替代发送参考。** sender上次真实值0、receiver上次被换成历史0.3、当前未篡改新包0.4、阈值0.09。真实sender应触发（0.16>0.09），receiver若使用假参考却会拒绝（0.01≤0.09）。攻击结束后仍可出现参考污染误拒绝。

**OPEN。** 当真实参考未知、触发条件与估计误差相关时，精确事件条件分布/集合及可部署检验尚需推导。不能直接使用固定日程健康高斯阈值；也不能通过假定可信序号/原包已知消除待研究问题。2026静默信息工作可能直接覆盖条件估计工具，应逐式核查。

## 8. F：噪声分布类重叠时不可能普遍识别

**PROVED，标准统计可辨识性边界。** 若两假设在接收端全部可观察历史上的概率律相同，则任意检验\(\varphi\)均有\(\Pr_0(\varphi=1)=\Pr_1(\varphi=1)\)，不能同时获得低误报和高检出。证明为同分布下任意可测函数的推前分布相同。

一个足够的具体机制是：正常允许独立隐私噪声\(\xi'\sim N(0,V+\Lambda)\)；攻击假设为正常噪声\(\xi\sim N(0,V)\)叠加独立\(a\sim N(0,\Lambda)\)。若所有噪声在时间/节点上的联合结构也按同样方式匹配，则包序列、后续滤波反馈及量测的联合可观察律相同。因而不能通过多收几包普遍分开两假设。

限制很关键：若公开固定了可信V，或者攻击改变了时间相关而正常明确要求独立，则不再是这个完全同分布反例。反之，只匹配一拍边缘方差不足以断言整个历史同分布；本例明确匹配全部联合生成结构。

此边界说明需要可信噪声策略/协方差范围/独立性承诺等额外资源，而不是再加一个方差检测模块。Ye的False Noise Attack原始假设及鲁棒噪声估计是直接近邻，未排重之前不提出“隐私伪装”创新。

## 9. 可复现的解析检查

[theory_checks.py](code/theory_checks.py)已独立运行，结果见 [g4_theory_20261113_v1/checks.json](results/g4_theory_20261113_v1/checks.json)。保存了B有害新包、D事件通过/参考污染、F同分布，以及T-B2的数值trace界例子；无Monte Carlo、无检测器拟合。复现须使用新Run ID：

```powershell
.venv/Scripts/python.exe reviews/g4_topic_screen/code/theory_checks.py --run-id g4_theory_reproduce
```

这些例子是对泛化命题的解析反例/代数核验，不证明当前五节点某一攻击seed必然出现同样状态，也不证明某候选有性能优势。

## 10. 结合本轮证据的研究判断

`EXPERIMENTAL`：B的小预算筛选实际Run为 [2026-11-13_g4_recovery_budget_r01](results/2026-11-13_g4_recovery_budget_r01/summary.json)，详细口径见 [04_minimal_value_of_recovery.md](04_minimal_value_of_recovery.md)。已通知的结果是强基线在有限候选日程中的oracle真实累计MSE改善约1.69%—1.91%，固定/随机不足0.5%，没有达到预先实际收益门槛；类似改善大多也见于健康同日程发送，不能归为攻击特异恢复增量。

因此本轮**停止B的当前模型/预算/候选时隙实例**，不实施残差调度器，不通过增加时隙或预算寻找正例。有限候选集合的上限不是全体可行调度的全局上限；负结果也不是“所有主动恢复均无价值”的定理。

G3的 [执行记录](../g3_partial_observability/execution_report.md)确认正常资格通过、pilot Gate A未通过；具体原因是正常代价/性能权衡未获所需证据及区间精度不足，后续合法证据Gate B尚未运行；不能写成“已证明本地后续量测无信息”。A不进入算法开发，理论候选仍是条件工具。数学上可写出(B.10)/(C.2)并不推翻这一停止决定，也不构成学报创新已成立的证据。
