# 误差递推、停止注入与时域统一上界

本报告采用00_scope中的模型。令 \(r_1=R,\ r_0=R+Z^{-1}\)，
\[
K_i(p)=\frac p{p+r_i},\quad
\beta_i(p)=1-K_i(p)=\frac{r_i}{p+r_i},\quad
F_i(p)=\frac{pr_i}{p+r_i}.
\]
协方差 \(P_t^+=F_{\gamma_t}(P_t^-)\)、\(P_{t+1}^-=A^2P_t^++Q\)。增益不是固定初始值。

## 1. 逐路径比较：需要一个真正保持记录的策略

健康/受攻运行共享物理初态、全部噪声和触发均匀数，另有独立攻击私有种子 \(\omega_a\)。设策略使 \((\gamma_{0:T},c_{0:T})\) 在这个耦合中几乎处处一致。不能事后条件在“未分叉”子样本上来替代这一假设。

令 \(e_t=m_t^{a,+}-m_t^{0,+}\)，初始 \(m_0^{a,-}=m_0^{0,-}\)。两运行同事件，所以协方差及增益相同。分别相减发送/静默更新得到
\[
e_0=\gamma_0K_1(P_0)a_0,\qquad
e_t=A\beta_{\gamma_t}(P_t^-)e_{t-1}
       +\gamma_tK_1(P_t^-)a_t,\quad t\ge1.
\tag{1}
\]
静默项的消去使用同一个实际量化中心；即使当拍无攻击，若码字已不同就不能沿用(1)。

设 \(\alpha_t=A\beta_{\gamma_t}(P_t^-)\)、空乘积为1，有限传播为
\[
e_t=\sum_{s=0}^t\gamma_sK_1(P_s^-)a_s
          \prod_{j=s+1}^t\alpha_j .
\tag{2}
\]
停止注入后仍须保持共同事件/码字路径，才能使用对应乘积。若共同路径上 \(|\alpha_j|\le\kappa<1\)，则 \(|e_t|\le\kappa^{t-\tau}|e_\tau|\)；但这个充分条件不是原模型自动具备的结论，也不自动保证未来码字继续相同。

## 2. 量化格硬约束及真实MSE

记录包含 \(c_{t+1}\)，同码即 \(Am_t^{a,+}\)、\(Am_t^{0,+}\) 属于同一个宽度 \(2\delta\) 的半开格。因此对 \(0\le t<T\)，
\[
|Ae_t|<2\delta,\qquad |e_t|\le2\delta/|A|,\qquad
\sum_{t=0}^{T-1}e_t^2\le4T\delta^2/A^2.
\tag{3}
\]
数学上两有限点的距离严格小于格宽，使用非严格上界便于统一表达。该界与开环稳定性无关。若日志只到 \(T-1\)，末拍 \(e_{T-1}\) 没有下一码字约束，不能直接写相同结论。

健康完整真实观测历史 \(\mathcal H_t^0\) 含健康事件与已发真实量测；正确的量化静默更新保证
\[
m_t^{0,+}=\mathbb E[x_t\mid\mathcal H_t^0].
\]
健康轨迹不依赖攻击种子，且在逐路径保持前提下，攻击估计和 \(e_t\) 对 \(\mathcal H_t^0\vee\sigma(\omega_a)\) 可测：攻击方可以用其合法真实发送历史重建一个健康影子估计器。于是
\[
\mathbb E[(x_t-m_t^{0,+})e_t]=0,\qquad
\boxed{J_t=\mathbb E e_t^2}.
\tag{4}
\]
这里交叉项消失不要求动作是独立随机符号，而要求健康条件均值、独立私有种子和整段耦合一致。得到
\[
0\le\frac1T\sum_{t<T}J_t\le4\delta^2/A^2.
\tag{5}
\]
若只是总体记录同律，(4)里的同物理健康估计差不再是正确的一般工具；见第4节。

## 3. \(Q>0\) 时的统一收缩：无需每拍欧氏系数小于1

以下假设 \(Q>0\)。设 \(r_0=R+Z^{-1}\)。所有 \(t\) 上 \(0<P_t^+<r_0\)，对 \(t\ge1\) 有 \(P_t^-\ge Q\)。因此
\[
\beta_{\gamma_t}(P_t^-)\le\theta:=\frac{r_0}{Q+r_0}<1,\qquad q=\sqrt\theta<1.
\tag{6}
\]
式(6)用于 \(t\ge1\) 的传播；初始t=0只需下面发送注入的界，不要求 \(P_0\ge Q\)。
对任何满足(1)的齐次传播，记 \(z_t=e_t/\sqrt{P_t^+}\)。因为 \(P_t^+=\beta_tP_t^-\)、\(P_t^-=A^2P_{t-1}^++Q\)，
\[
\left|A\beta_t\sqrt{\frac{P_{t-1}^+}{P_t^+}}\right|^2
=\beta_t\frac{A^2P_{t-1}^+}{P_t^-}
=\beta_t\left(1-\frac Q{P_t^-}\right)\le\theta.
\tag{7}
\]
发送注入满足
\[
\frac{K_1(P_t^-)}{\sqrt{P_t^+}}
=\frac{\sqrt{K_1(P_t^-)}}{\sqrt R}\le R^{-1/2}.
\]
因此从相同初值出发，对全部 \(|a_t|\le b\)：
\[
|z_t|\le\frac b{\sqrt R}\sum_{j=0}^t q^j,\qquad
|e_t|\le r_*b,\quad
r_*=\frac{\sqrt{r_0/R}}{1-q}.
\tag{8}
\]
停止注入后，只要还可作共同路径比较，
\[
|e_t|\le\sqrt{\frac{P_t^+}{P_\tau^+}}\,
q^{t-\tau}|e_\tau|.
\tag{9}
\]
由于 \(P_t^+\ge\underline P^+:=\min\{F_1(P_0),F_1(Q)\}>0\)，其前置常数也可统一控制。界通常保守；它不是求最坏传播常数。

原信息域下的真实条件均值记 \(\mu_t^+\)，受攻条件偏差 \(D_t=\mu_t^+-m_t^{a,+}\)。对任意合法因果攻击，条件高斯递推给
\[
D_0=-\gamma_0K_1(P_0)a_0,\qquad
D_t=A\beta_{\gamma_t}(P_t^-)D_{t-1}
-\gamma_tK_1(P_t^-)a_t.
\tag{10}
\]
这里两估计使用的是同一受攻分析历史和同一实际码中心，故(10)不要求与健康路径同码。相同归一化证明给 \(|D_t|\le r_*b\) 对所有t成立。

没有把(9)变成跨越码字分叉后的健康/受攻路径比较；但(10)可独立用于全策略损伤上界。

这里的一般性仍限于原模型的合法信息域：给定已发送的真实量测及独立攻击种子，而不是给定隐藏状态或未发送的真实量测。量化实际码是该扩充历史的可测函数，所以健康/受攻条件均值的静默更新均用同一码，量化平移项才消去。不能将这一条件高斯结论直接搬到仅由受污染载荷构成的较小信息域。

## 4. 整段记录TV的时间一致上界（\(Q>0\)）

令 \(R_T=(\gamma_{0:T},c_{0:T})\)、\(\Delta_T\le\varepsilon\)。事件前缀决定 \(P_t^+\)，因此
\[
(P_t^+,c_{t+1},\gamma_{t+1})
\]
是 \(R_T\) 的确定投影，任意 \(t<T\) 的投影TV也不超过epsilon。此处不要求同物理耦合逐路径一致。

固定 \(b\le b_{\rm ref}\)、\(\delta\le\delta_{\rm ref}\)，所有t有
\[
V_t=Z^{-1}+A^2P_t^++Q+R\le
\overline V=Z^{-1}+A^2r_0+Q+R,
\quad h_t=A^2/(2V_t)\ge h_*=A^2/(2\overline V)>0.
\]
取
\[
B_*=r_*b_{\rm ref}+\delta_{\rm ref}/|A|,\quad
\chi_*=\frac{1-e^{-h_*B_*^2}}{B_*^2},\quad
C_0=\frac1{2(Z^{-1}+Q+R)},\quad
M_*=\sqrt{1+Z(A^2r_0+Q+R)}.
\tag{11}
\]
记量化误差 \(\xi_{t+1}=c_{t+1}-m_{t+1}^{a,-}\)、\(|\xi_{t+1}|\le\delta\)。原条件概率恒等式为
\[
\mathbb E_\pi[W_t\mid\mathcal G_t^+]
=e^{-h_t(D_t-\xi_{t+1}/A)^2},\qquad
W_t=\frac{\mathbf1_{\{\gamma_{t+1}=0\}}}{s(P_t^+)},\quad
0\le W_t\le M_*.
\]
健康条件偏差为零，所以 \(1-\mathbb E_0W_t\le C_0\delta^2\)；TV控制有界统计量，故
\[
\chi_*\mathbb E_\pi(D_t-\xi_{t+1}/A)^2
\le1-\mathbb E_\pi W_t
\le C_0\delta^2+M_*\varepsilon.
\tag{12}
\]
真实MSE分解依旧是
\[
J_t=\mathbb E_\pi D_t^2+
\mathbb E_\pi P_t^+-\mathbb E_0P_t^+.
\]
后两项不能丢弃，其绝对值不超过 \(r_0\varepsilon\)。由三角不等式和(8)–(12)，对所有t<T：
\[
J_t\le
\min\left\{r_*^2b^2,\
\left(\sqrt{(C_0\delta^2+M_*\varepsilon)/\chi_*}
+\delta/|A|\right)^2\right\}+r_0\varepsilon.
\tag{13}
\]
从而对用户定义的平均最坏损伤，
\[
\boxed{\mathcal V_T(b,\delta,\varepsilon)
\le (2C_0/\chi_*+2/A^2)\delta^2
 +(2M_*/\chi_*+r_0)\varepsilon}
\tag{14}
\]
的常数不依赖T。零策略可行保证最坏值非负；单条非零TV策略的J_t仍可为负。特别地
\[
\mathcal V_T(b,\delta,0)
\le\min\{r_*^2b^2,C_\delta\delta^2\},
\quad C_\delta=(\sqrt{C_0/\chi_*}+|A|^{-1})^2.
\tag{15}
\]
这是**整个历史TV类**的上界，不是把逐路径格宽约束直接套到同律类。它是原概率证书加时间一致归一化半径的结果，不独立宣称新颖性；未证明非零TV匹配下界。

量词为：固定 \(A\ne0,P_0,R,Z,Q>0\)（Q正，其余按原模型）、正有限 \(b_{\rm ref},\delta_{\rm ref}\) 后，存在上面给出的正有限常数，对所有整数 \(T\ge1\)、\(0\le b\le b_{\rm ref}\)、\(0<\delta\le\delta_{\rm ref}\)、\(0\le\varepsilon\le1\)，以及全部满足整段TV预算的合法因果策略成立。这里
\[
\mathcal V_T=\sup_{\pi:\ |a_t|\le b,\ \Delta_T\le\varepsilon}
\frac1T\sum_{t=0}^{T-1}J_t(\pi).
\]
同一策略必须满足整个前缀预算，证明没有把每拍各自可行的不同策略拼成一条策略。\(C_\delta\) 是便于表示的常数名称，不随实际delta或T变化。

## 5. \(Q=0\) 边界与初始系数的局限

Q=0时(6)给theta=1，不能从本证明取得同样的时间一致常数。逐路径格宽界(3)仍成立。对无注入的共同路径，有精确乘积恒等式
\[
\prod_{j=s+1}^t A\beta_j
=A^{-(t-s)}\frac{P_t^+}{P_s^+}.
\tag{16}
\]
例如A=1,Q=0时，后验精度满足
\(1/P_t^+=1/P_s^++\sum_{j=s+1}^t1/r_{\gamma_j}\)，
所以停止注入的差值至少按O(1/(t-s))衰减，但不是由本证明得到统一指数率。Q=0的一般全策略长期TV紧界未完成。

若停止注入后的真实事件序列为\(\gamma_t\)，从时刻\(\tau\)起先假设路径相同，则(1)的解为
\[
e_n=e_\tau\prod_{j=\tau+1}^nA\beta_{\gamma_j}(P_j^-).
\]
定义健康下一预测的格内余量
\[
r_{n+1}^{\rm cell}=\delta-|Am_n^{0,+}-Q_\delta(Am_n^{0,+})|.
\]
若对该实际健康路径的每个未来n都有
\[
|A|\ |e_n|<r_{n+1}^{\rm cell},
\tag{17}
\]
则归纳可证下一码仍相同，静默/发送事件也因共用真实量测与触发均匀数而相同，故路径保持可以继续。若余量为零或不满足该条件，只能说该充分性证明停止；不代表一定分叉。这是路径条件而非总体长期正概率保证。量化格余量会随健康预测相位变化，故平均收缩系数小于一并不足以单独推出全程码保持。

初始系数的确定性计算（初值P0=.8,R=.2，量化误差暂置零）为：
\[
K_1=.8,\quad K_0=.8/(.8+.7)=.533333\ldots,
\quad
\begin{array}{c|cc}
 & \text{发送 }A(1-K_1)&\text{静默 }A(1-K_0)\\\hline
S1,\ A=.82&.164&.382667\\
U1,\ A=1.04&.208&.485333
\end{array}
\]
这只是第0拍数值，后续增益会随事件协方差变化。它不能替代(7)的时间一致界，开环 \(|A|>1\) 不能直接推出估计污染发散，局部收缩也不能保证不跨量化格。
