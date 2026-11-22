# 精确似然反演、污染下界与输出校正风险

基准提交 e1c55269；日期 2026-11-22。本文件是阶段四的解析理论审查，不生成随机性能样本、不修改旧阶段文件。置信失效概率记为 \(\varepsilon\in(0,1)\)，量化半步长另记为 \(\delta_q\)，避免两者混用。

结论：任意序贯一致的正规化参考分布都可以作似然反演的分子；分母必须保留真实参数对应的精确物理似然。由该置信集合得到的当前污染下界，可用于同一 monitor 输出的保守校正，并有全时域高概率条件风险保证及有限时域期望 MSE 预算。覆盖保证不自动证明认证集合收缩、数值实现可认证或实际恢复已有收益。

## 1. 必须固定的模型与合法历史

以下采用接收端可获**精确反馈中心**、可信事件位和实际连续发送载荷的阶段三分支。只不保存原始随机相位字段不构成障碍：中心 \(c_t\) 和本地预测 \(m_t^-\) 给出 \(r_t=c_t-m_t^-\)。但如果接收记录只有整数索引而隐藏过去真实中心，静默更新依赖未记录中心，条件先验一般是高斯混合；不能直接沿用本文件的单高斯递推。

令 \(\mathcal I_t\) 为时刻 \(t\) 当前事件和发送载荷处理完成后的合法接收历史；\(\mathcal I_t^-\) 还未包括当前事件/载荷，但已包括当前反馈中心。对于固定真实参数
\[
\vartheta=(k,b),\qquad k\in\mathbb N_0,\quad 0\le b\le b_{\max},
\]
仅在 \(t\ge k,\gamma_t=1\) 时在真实载荷上加 \(b\)。另以 \(\varnothing\) 表示无攻击。原 monitor 始终使用实际收到的载荷和实际中心，并继续产生下一反馈；校正结果不回写 monitor。

给定同一个接收历史，monitor 的 \(m_t^\pm,P_t^\pm,K_{\gamma_t}\) 是固定算法的函数，候选参数改变的是潜在真状态的条件均值。定义
\[
H_{k,0}^-=0,\qquad
H_{k,t}^+=(1-K_{\gamma_t})H_{k,t}^-
+\gamma_tK_1\mathbf1_{\{t\ge k\}},\qquad
H_{k,t+1}^-=A H_{k,t}^+.
\tag{1}
\]
在 \(A>0\)、攻击前正确健康初始化下，\(H_{k,t}^\pm\ge0\)，并有
\[
\mu_t^\vartheta=\mathbb E_\vartheta[x_t\mid\mathcal I_t]
=m_t^a-bH_{k,t}^+,\qquad
\theta_t(\vartheta)=m_t^a-\mu_t^\vartheta=bH_{k,t}^+.
\tag{2}
\]
发送时，给定真实参数，\(y_t=\widetilde y_t-b\mathbf1_{\{t\ge k\}}\) 可由载荷反演；发送选择因子在状态后验归一化中消去。静默时，用同一个已知中心作高斯更新。因此
\[
\operatorname{Var}_\vartheta(x_t\mid\mathcal I_t)=P_t^+
\tag{3}
\]
与名义事件协方差标签相同。这不是另外生成一条健康反事实轨道，也不需要知道真实状态。

## 2. 精确参数似然与任意参考预测分布

设 \(p_{\vartheta,t}=p_\vartheta(O_{0:t})\) 为中心、事件和发送载荷的精确历史密度，\(p_{0,t}\) 为健康历史密度，\(p_{\vartheta,-1}=p_{0,-1}=1\)。每一步都使用阶段三联合核
\[
G_\vartheta=s_t\exp[-(d_{\vartheta,t}-r_t)^2/(2V_t)],
\]
\[
f_\vartheta(u)=\phi_{S_t}(u-b_t-d_{\vartheta,t})
\left[1-e^{-Z(u-b_t-r_t)^2/2}\right],
\quad b_t=b\mathbf1_{\{t\ge k\}},\quad d_{\vartheta,t}=-bH_{k,t}^-.
\tag{4}
\]
健康和候选的中心条件分布共同，因子抵消。送达载荷的密度在孤立位置为零，但对任意两个固定参数，有限时间记录的概率测度仍彼此绝对连续；不能把单点零密度当作具有正质量的支持缺口。

现在选一个参考概率过程 \(Q\)，其有限历史密度 \(q_t\) 必须满足：

- \(q_{-1}=1\)，每拍预测核正规化；
- 预测核只依赖已见历史，不能偷看本拍事件或载荷后再挑选；
- 各时刻有限历史密度具有投影一致性；
- 对每个被声称覆盖的真实参数，\(Q_t\ll P_{\vartheta,t}\)。

不要求 \(Q\) 属于物理攻击族，更不要求其候选网格含真实 \(b\)。例如阶段三完整J1或P1的**当前检验过程** \(E_t\) 为非负、均值1的健康鞅时，
\[
q_t:=E_t p_{0,t}
\tag{5}
\]
给出相容的有限历史概率密度：鞅性质保证投影一致性；标准Borel序列空间上可据此定义预测分布。P1保留健康事件概率、改变发送条件载荷分布，也是正规化的人工预测核，不必声称它是某个真实攻击模型。

以下对象不可不加证明地替代 \(E_t\)：运行最大值 \(\max_{s\le t}E_s\)、检测器的二值报警标记、任意截断/重归一化分数、观察本拍数据后选择最有利候选。它们未必是初值1的密度鞅。若有意采用非负超鞅，仍可能构造有效e-process覆盖，但不能再无条件称 \(q_t\) 为正规化且投影一致的概率密度；本文件只使用式(5)的鞅版本。

## 3. 定理：连续参数族的全时域置信覆盖

定义
\[
\Lambda_t(\vartheta)=\frac{p_{\vartheta,t}}{p_{0,t}},\qquad
C_t^\varepsilon=
\{\vartheta:p_{\vartheta,t}>\varepsilon q_t\}
=\{\vartheta:\Lambda_t(\vartheta)>\varepsilon E_t\}.
\tag{6}
\]
对每一个固定真实参数 \(\vartheta^\star\)，有
\[
\boxed{\Pr_{\vartheta^\star}
 \{\forall t\ge0:\vartheta^\star\in C_t^\varepsilon\}\ge1-\varepsilon.}
\tag{7}
\]

证明：在 \(P_{\vartheta^\star}\) 下，
\[
M_t(\vartheta^\star)=q_t/p_{\vartheta^\star,t}
\]
是初值1的非负密度鞅，逐拍条件期望等于前一时刻值。Ville不等式给
\[
\Pr_{\vartheta^\star}\{\sup_t M_t(\vartheta^\star)\ge1/\varepsilon\}
\le\varepsilon.
\]
非排除事件正是式(7)。对数实现可比较
\(\log p_{\vartheta,t}-\log p_{0,t}>\log\varepsilon+\log E_t\)，但必须保留数学零点，不随意夹密度。\(\square\)

这里是**对每个固定真参数的统一时间覆盖**，不是“同一概率事件同时覆盖所有假想真参数”。不需对不可数参数再作并合界。实际集合可含全部 \(k\ge0,b\in[0,b_{\max}]\)，即使 \(Q\) 仅用三档幅值构造，式(7)仍覆盖网格外真值，前提是它使用的是该真值的精确分母。将分母也投到三档网格会改变命题。

式(7)不保证 \(C_t^\varepsilon\) 单调缩小。集合可以离开又重入；全时域覆盖来自同一个鞅的最大不等式。若要额外取历史交集，须对每个参数在各时刻的精确似然都正确计算，交集仍有式(7)覆盖；但其污染投影必须用当前时刻函数 \(\theta_t(\vartheta)\)，不能把过去污染数值直接交集。

## 4. 投影到当前污染与数值外包要求

设已知全历史上界 \(0\le\theta_t(\vartheta)\le B_{\max}\)。对非空集合定义
\[
\ell_t^{\rm exact}=\inf_{\vartheta\in C_t^\varepsilon}\theta_t(\vartheta).
\]
实现输出 \(\widehat L_t\) 必须满足
\[
0\le\widehat L_t\le
\min\{B_{\max},\ell_t^{\rm exact}\}.
\tag{8}
\]
集合为空、求解未完成或无法认证时，输出 \(\widehat L_t=0\)。常用的安全近似是保留一个外集合
\(\widehat C_t\supseteq C_t^\varepsilon\)，再对其求下界；删除未被严格排除的起点/幅值会把下界虚抬。

在式(7)的覆盖事件 \(\mathcal C\) 上，
\[
\boxed{\forall t:\quad 0\le\widehat L_t\le\theta_t^\star.}
\tag{9}
\]
所以对固定真参数，全时域下界失效概率不超过 \(\varepsilon\)。真参数不在 \(Q\) 的幅值网格不会破坏该结论；粗数值网格不能确保式(8)，可能破坏它。

对固定时刻 \(t\)，所有 \(k>t\) 在已见历史上都等价于健康模型且污染为0。它们可合并为一个“尚未开始”类；在精确混合分子中应合并其尾质量，而非丢掉。已经开始的起点只有 \(k=0,\ldots,t\)，但每个仍有连续幅值区间。

可测性也可在此有限表示下处理：对每个起点，非对数历史似然及 \(bH_{k,t}^+\) 随 \(b\) 连续，严格保留条件给相对开可行集；其inf可用稠密可数幅值点加端点逼近。再对有限起点和未启动类取inf即可。实际数值认证仍需上包络，不能把这一可测性论证当成有限网格已足够。

若认证方法检验
\[
\sup_{\vartheta:\theta_t(\vartheta)\le z}\log\Lambda_t(\vartheta)
<\log(\varepsilon E_t),
\tag{10}
\]
则所有污染不超过 \(z\) 的候选均被排除；非空真实置信集合的污染inf至少为 \(z\)。数值实现应有右端阈值的可靠下界与左端上确界的可靠上界；单纯返回某个优化器局部最大值并不构成证明。空集时仍须执行零动作规则，不能让“空集inf=+∞”导致无限校正。

## 5. 报警、正污染认证与有用认证的关系

取同一个参考过程，定义
\[
\tau_{\rm detect}=\inf\{t:E_t\ge1/\varepsilon\},\qquad
\tau_{\rm safe}(g)=\inf\{t:\widehat L_t^2\ge g\},\quad g>0.
\tag{11}
\]
无攻击参数始终满足 \(\Lambda_t(\varnothing)=1,\theta_t(\varnothing)=0\)。若 \(E_t<1/\varepsilon\)，健康参数严格留在(6)，所以任何合法下界(8)只能为0。因此
\[
\boxed{\tau_{\rm detect}\le\tau_{\rm safe}(g)}
\tag{12}
\]
对所有输入路径成立，只要使用同一 \(\varepsilon\)、参考过程和包含健康/未启动类的精确反演。若另设检测阈值、参考预测或修剪候选，需重新比较。

**严格越阈与微小正下界。** 固定有限 \(t\)，在 \(A>0\)、\(0<K_\gamma<1\) 下，\(\theta_t(k,b)=0\) 只有 \(b=0\) 或从 \(k\) 到 \(t\) 尚无发送。在这些情况下所有实际攻击输入均为0，故 \(\Lambda_t=1\)。对有限个有效起点、紧幅值区间和连续的非对数历史似然，若
\[
E_t>1/\varepsilon,\qquad C_t^\varepsilon\ne\varnothing,
\]
则 \(\inf_{C_t^\varepsilon}\theta_t>0\)。否则可从污染趋零的候选序列抽取同一起点和收敛幅值子序列；极限污染0给似然1，而保留候选的极限似然至少 \(\varepsilon E_t>1\)，矛盾。

这使用严格间隙。恰好 \(E_t=1/\varepsilon\) 时，不保证inf正；数值求解保守返回0时，即使严格越阈也可能没有**已计算出的**正证书。更不能从“正”推到工程规模。取 \(g>0\) 是必要区分。

此外，污染在长静默阶段衰减。即使参数集合的污染函数误差趋零，也不说明每一个充分晚时刻都有 \(\widehat L_t^2\ge g\)，或任意指定 \(g\) 的认证时间均有有限上界。若 \(g>B_{\max}^2\)，该门必不可能通过。发送时 \(\theta_t^\star\ge k_-b^\star\) 可用于把函数收缩与有效认证机会连接，但需要另行给出发送机会、集合收缩和 \(g<(k_-b^\star)^2\) 的条件，不能仅凭高检出率推断。

## 6. 定理：下界校正的最坏风险改善

令校正只作用于输出
\[
m_t^r=m_t^a-c_t,\qquad c_t\ge0,
\]
其中 \(c_t\) 是 \(\mathcal I_t\)-可测。真实参数固定为 \(\vartheta^\star\)，由条件均值正交性，
\[
R_t^a:=\mathbb E_{\vartheta^\star}[(x_t-m_t^a)^2\mid\mathcal I_t]
=P_t^++(\theta_t^\star)^2,
\]
\[
R_t^r=P_t^++(\theta_t^\star-c_t)^2,\qquad
\boxed{\Delta R_t:=R_t^a-R_t^r=2\theta_t^\star c_t-c_t^2.}
\tag{13}
\]
这不需要另一个恢复滤波器，也不需要估计两支路交叉协方差。

若可兼容污染值属于非负区间 \([L_t,U_t]\)，则对 \(c\ge0\)，
\[
\inf_{\theta\in[L_t,U_t]}(2\theta c-c^2)=2L_tc-c^2.
\]
右端严格凹，最大值在 \(c=L_t\) 取得：
\[
\boxed{\sup_{c\ge0}\inf_{\theta\in[L_t,U_t]}\Delta R_t=L_t^2.}
\tag{14}
\]
若污染集合非区间但inf为 \(L_t\)，同样成立；inf不必被取到。其目标是**相对monitor的最坏改善**，不是最坏绝对风险最小化，不能与选区间中点的不同优化目标混称。

实施 \(c_t=\widehat L_t\) 后，在覆盖事件上
\[
\Delta R_t=2\theta_t^\star\widehat L_t-\widehat L_t^2
\ge\widehat L_t^2\ge0.
\tag{15}
\]
从而
\[
\Pr_{\vartheta^\star}\{\forall t:R_t^r\le R_t^a\}\ge1-\varepsilon.
\tag{16}
\]
这里风险是给定当前合法历史的条件MSE，覆盖事件则是这些随机条件风险在全时域同时满足不等式的事件。它不是逐样本平方误差保证；某一真实状态实现的 \((x_t-m_t^r)^2\) 仍可能更大。

## 7. 有限时域期望累计MSE预算

假设输出强制截在 \(0\le\widehat L_t\le B_{\max}\)，且真实污染非负。在任意输入历史上，
\(\Delta R_t\ge-\widehat L_t^2\)。因此逐路径有
\[
\Delta R_t\ge\widehat L_t^2
-2\mathbf1_{\mathcal C^c}\widehat L_t^2.
\tag{17}
\]
对任意固定、有限的评价时刻集合 \(\mathcal T\)，\(|\mathcal T|=T\)，求和取期望得到
\[
\boxed{
\mathbb E_{\vartheta^\star}\sum_{t\in\mathcal T}
\big[(x_t-m_t^a)^2-(x_t-m_t^r)^2\big]
=\mathbb E_{\vartheta^\star}\sum_{t\in\mathcal T}\Delta R_t
\ge
\mathbb E_{\vartheta^\star}\sum_{t\in\mathcal T}\widehat L_t^2
-2\varepsilon T B_{\max}^2.}
\tag{18}
\]
即使全时域覆盖事件 \(\mathcal C\) 依赖未来，式(17)仍是路径上的代数界；不把 \(\mathcal C\) 加进状态条件分布或误用条件正交性。先在 \(\mathcal I_t\) 下得到(13)，再对(17)积分即可。

式(18)是相对于同一受攻击观测/反馈轨道上的原monitor，而不是无攻击健康轨道。两支路共有 \(P_t^+\)，所以协方差项在该比较中精确抵消。若校正结果反馈进触发器，记录与未来条件分布改变，现有置信核与风险比较均需重做。

期望累计降损的充分条件是
\[
\mathbb E\sum_{t\in\mathcal T}\widehat L_t^2
>2\varepsilon T B_{\max}^2.
\tag{19}
\]
它不从覆盖本身推出。若只在 \(\widehat L_t^2\ge g\) 时行动，记这样的动作数为 \(N_g\)，则
\(\mathbb E\sum c_t^2\ge g\,\mathbb E N_g\)；充分条件可写为
\(g\,\mathbb E N_g/T>2\varepsilon B_{\max}^2\)。门槛很小而动作稀少时，可能永远无法由此充分界证明期望收益。

对无攻击真参数，\(\theta_t^\star=0\)，在覆盖事件上全时域 \(c_t=0\)。因此可另给更紧的健康代价界
\[
\Pr_0\{\exists t:c_t>0\}\le\varepsilon,\qquad
\mathbb E_0\sum_{t\in\mathcal T}(R_t^r-R_t^a)
=\mathbb E_0\sum c_t^2\le\varepsilon T B_{\max}^2.
\tag{20}
\]
该健康特例的系数是1，不必使用一般攻击式(18)的系数2。

式(18)目前针对固定有限 \(T\)。若用无界随机评价时长，不能直接把 \(T\) 替换为 \(\mathbb E T\) 后仍乘同一个 \(\varepsilon\)，因为失效事件与随机时长可能相关；需有确定截断或额外可积加权论证。

## 8. S1/U1污染幅值与风险预算

先验协方差满足阶段二Riccati不变区间。令发送增益 \(K\in[k_-,k_+]\)，静默传播系数小于1；持续非负攻击的后验污染递推是
\[
\theta_t=A(1-K_{\gamma_t})\theta_{t-1}+\gamma_tK_1b.
\]
若 \(1-A(1-k_-)>0\)，取
\[
c_B=\max_{K\in[k_-,k_+]}\frac K{1-A(1-K)},\qquad
B_{\max}=c_B b_{\max}.
\tag{21}
\]
发送时 \(A(1-K)B_{\max}+Kb_{\max}\le B_{\max}\)，静默时也不离开区间，所以(21)覆盖所有候选起点及全部允许事件历史。S1的最大值在 \(k_+=0.8\)，U1在 \(k_-=0.4091834821\)。

对 \(b_{\max}=0.25,\varepsilon=0.01\)：

| 模型 | \(B_{\max}\) | 一般攻击每拍预算 \(2\varepsilon B_{\max}^2\) | 健康每拍上限 \(\varepsilon B_{\max}^2\) |
|---|---:|---:|---:|
| S1 | 0.2392344498 | 0.0011446624 | 0.0005723312 |
| U1 | 0.2653239595 | 0.0014079361 | 0.0007039680 |

这些是解析预算的确定性显示值，不是已观察到的恢复收益，也不是数值区间认证。完整复算见 [compute_risk_budgets.py](compute_risk_budgets.py)、[risk_budgets.json](risk_budgets.json)。

## 9. 本阶段可以声明什么

可以声明：在精确中心、连续载荷与正确模型分支中，以任意合法预测分布作分子、精确参数似然作分母，可得到全时域污染下界；用该下界校正同一monitor输出，是置信相容集合中最坏条件风险改善的最优非负动作，并有显式有限时域期望预算。

不能声明：J1报警分数本身已估计了攻击幅值；warm参考预测下置信集合必然快速收缩；有限字长或index-only历史也自动具有本高斯核；数值优化局部解已经给出认证下界；校正后的总MSE已经经实验降低。本轮没有生成恢复性能样本。
