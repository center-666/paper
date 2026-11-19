# 一般k：历史一致的概率下界、匹配阶数和全策略上界

## 1. 全历史条件的统一W^{1,1}界

式(1)的发送次密度导数为
\[
f'_{P,e}(u)=\phi'_S(u)[1-g(u-e)]-\phi_S(u)g'(u-e).
\]
对所有e平移一致地，
\[
\|f'_{P,e}\|_1\le\sqrt{2/(\pi S)}+\sup_x|g'(x)|
=\sqrt{2/(\pi S)}+\sqrt{Z/\mathrm e}.
\]
P在固定k下仅取有限值集。令S_min=min_h(P_h+R)>0，则统一界
\[
L_f=\sqrt{2/(\pi S_{min})}+\sqrt{Z/\mathrm e}<\infty.
\tag{5}
\]
当前量化相位e依历史变化并不破坏该界，因为g′的上确界与中心平移无关。

当前发送概率的静默项可解析积分：
\[
E[g(u-e)|\zeta]=s_P\exp[-Ze^2/(2(1+ZS_P))],\quad
s_P=(1+ZS_P)^{-1/2}.
\]
故对所有前史、量化相位，\(P(\gamma_k=1|\zeta)\ge p_*:=\min_h(1-s_{P_h})>0\)。这一步阻止所选安全区条件化到概率趋零的发送分支。

仿射变量 \(M_k=A(m_k^-+K_hu)\) 的发送次密度为
\[
\rho_{h,e}(x)=\frac1{|AK_h|}f_{P_h,e}\!\left(\frac{x-Am_k^-}{AK_h}\right).
\]
其 \(\|\rho'\|_1\le L_*:=L_f/\alpha_{min}\)，其中 \(\alpha_{min}=\min_h|AK_h|>0\)。因此，即使m与e在无限多个历史取值上连续变化，M的条件发送密度仍有统一变差界。

## 2. 周期中央区的确定性平均引理

令 \(\chi_\delta=\mathbf1_{\mathcal C_\delta}\)。其周期为2δ、均值1/2，且存在周期原函数G满足
\[
G'=\chi_\delta-\tfrac12\text{ a.e.},\qquad \|G\|_\infty\le\delta/4.
\]
例如在一个周期边界处取G=0，中央半区上斜率+1/2，其余区间斜率−1/2，最大值再平移至0中心。

对每个历史前缀的发送次密度rho，分部积分：
\[
\left|\int\rho(x)\chi_\delta(x)dx-\tfrac12\int\rho(x)dx\right|
=\left|\int\rho'(x)G(x)dx\right|
\le\frac\delta4\|\rho'\|_1\le\frac\delta4L_*.
\tag{6}
\]
因发送质量至少p*，当 \(0<\delta\le\delta_*:=p_*/L_*\) 时，每个条件前史均满足
\[
P(\gamma_k=1,M_k\in\mathcal C_\delta\mid\zeta)
\ge p_*/2-\delta L_*/4\ge p_*/4.
\tag{7}
\]
对所有健康历史平均仍为p*/4。此证明不把M模格宽假设成均匀，也不假设u的量化相位独立；常数明确依赖k和固定模型。

## 3. 全因果攻击下界与攻击幅值联合关系

将式(7)代入式(4)：
\[
J_{k,\delta}\ge K_{min}^2\frac{p_*}{4}\min\left\{b^2,\frac{\delta^2}{4\alpha_{max}^2}\right\}
\ge c_k\min\{b^2,\delta^2\},
\]
\[
c_k=\frac{K_{min}^2p_*}{4}\min\{1,(4\alpha_{max}^2)^{-1}\}>0.
\tag{8}
\]
这对任意固定 \(0<b\le b_{ref}\) 和充分小 \(\delta\) 成立。目标前攻击全为零，目标后不再攻击，但它作为原因果攻击集合中的一个子类足以给最坏值下界。

## 4. 任意允许攻击下界及匹配上界

继承上一量化反馈全策略证书。有限时域的协方差集合有限，误差偏差递推给 \(|D_k|\le r_kb_{ref}\)。下一量化误差 \(e_{k+1}=c_{k+1}-m_{k+1}^-\) 统一满足|e|≤δ_ref。令
\[
V(P)=Z^{-1}+A^2P+Q+R,\quad h(P)=A^2/[2V(P)],
\quad W=\mathbf1_{\{\gamma_{k+1}=0\}}/s(P_k^+).
\]
给定扩充历史，\(E_\pi[W|\mathcal G_k^+]=e^{-h(P_k^+)(D_k-e_{k+1}/A)^2}\)。固定P集合上取 \(h_*>0,M<\infty,\Omega<\infty\)，并按 \(R_*=r_kb_{ref}+\delta_{ref}/|A|\) 取 \(q_*=(1-e^{-h_*R_*^2})/R_*^2\)。

若 \(\Delta^{full}_{\delta,k}=0\)，它蕴含marked投影 \((P_k^+,c_{k+1},\gamma_{k+1})\) 同律。于是 \(W\) 同律，而健康基准满足 \(0\le1-E_0W\le c_0\delta^2\)，其中 \(c_0=\max_P1/[2V(P)]\)。因此
\[
q_*E_\pi(D_k-e_{k+1}/A)^2\le1-E_\pi W\le c_0\delta^2.
\]
L2三角不等式和同律下协方差迹项相消，得
\[
J_{k,\delta}\le C_{\delta,k}\delta^2,
\quad C_{\delta,k}=\left(\sqrt{c_0/q_*}+|A|^{-1}\right)^2.
\tag{9}
\]
同时 \(J_{k,\delta}=E_\pi D_k^2\le r_k^2b^2\)，因为完整事件记录同律也使P_k+同律。因此
\[
V^{full,(k)}_{m,\delta}(b,0)\le\max\{r_k^2,C_{\delta,k}\}\min\{b^2,\delta^2\}.
\tag{10}
\]

合并(8)、(10)，对每个固定有限k、固定b_ref、δ≤δ_*及 \(0<b\le b_{ref}\)，
\[
\boxed{V^{full,(k)}_{m,\delta}(b,0)=\Theta_k(\min\{b^2,\delta^2\}).}
\tag{11}
\]
较小marked记录也成立：上界直接用marked同律，下界攻击对full记录逐路径同律。

常数依赖k。事件历史数、P_h极值、斜率alpha_min、p*及误差增益可能随k恶化；不推出时间一致下界、长期地板或\(\inf_k c_k>0\)。这也不是三预算 \(\varepsilon>0\) 联合定理。
