# 安全区间概率的统一下界与零TV损伤阶数

本报告均为DERIVED，沿用01的标量、首次攻击、无饱和反馈量化及记录定义。证明不依赖随机模拟，不声称一般时刻、全日志或固定有限比特推广。

## 1. 不把随δ变化的发送密度误当固定密度

令S=P0+R，K=P0/S，α=|AK|。健康初始反馈 \(c_{0,\delta}=\mathsf Q_\delta(m_0)\) 可随δ改变；其误差 \(e_{0,\delta}=c_{0,\delta}-m_0\) 满足|e0|≤δ。

发送概率为
\[
p_\delta=1-s_0e^{-e_{0,\delta}^2/(2V_0)},\quad
s_0=(1+ZS)^{-1/2},\quad V_0=Z^{-1}+S.
\]
设 \(p_*:=1-s_0>0\)，则 \(p_\delta\ge p_*\)，且δ→0时pδ→p*。零初值m0=0时c0恒为0、pδ=p*；以下证明不要求m0=0。

M的发送分支次概率密度为
\[
\rho_\delta(m)=\frac1\alpha f_\delta\!\left(m_0+\frac{m/A-m_0}{K}\right),\qquad
\int\rho_\delta=p_\delta.
\tag{1}
\]
fδ见01式(6)。用 \(0\le1-g\le1\)、\(\|\phi'_S\|_1=\sqrt{2/(\pi S)}\)、\(\sup|g'|=\sqrt{Z/\mathrm e}\)，有
\[
\|f'_\delta\|_1\le\sqrt{\frac2{\pi S}}+\sqrt{\frac Z{\mathrm e}},\qquad
\|\rho'_\delta\|_1\le L_*:=\frac1\alpha\left(\sqrt{\frac2{\pi S}}+\sqrt{\frac Z{\mathrm e}}\right).
\tag{2}
\]
这个W^{1,1}界对所有δ和初始量化相位统一成立。因此可以控制随δ变化的密度，而不是仅引用固定密度的“安全面积占一半”直觉。

## 2. 周期指示函数的显式积分界

定义每格中间一半
\[
A_\delta=\bigcup_{j\in\mathbb Z}(2j\delta-\delta/2,\,2j\delta+\delta/2),\qquad
\chi_\delta=\mathbf1_{A_\delta}.
\]
它与 \(d_\delta(M)>\delta/2\) 等价（边界零测）。\(\chi_\delta-1/2\) 为周期2δ、均值零的函数。在基元[−δ,δ]上，其从−δ起的积分先由0降至−δ/4，再升至δ/4，最后回到0。把此积分函数周期延拓为Gδ，则
\[
G'_\delta=\chi_\delta-\tfrac12\ \text{a.e.},\qquad
\|G_\delta\|_\infty\le\delta/4.
\]
ρδ绝对连续、两端趋零，分部积分及(2)给
\[
\left|\int\rho_\delta(m)\chi_\delta(m)\,dm-\tfrac12p_\delta\right|
=\left|\int\rho'_\delta(m)G_\delta(m)\,dm\right|
\le\frac{\delta L_*}{4}.
\tag{3}
\]
这是严格的统一概率估计，不假设M模2δ恰好均匀。

因此只要 \(0<\delta\le\delta_0:=p_*/L_*\)，
\[
P(\gamma_0=1,M\in A_\delta)
\ge p_*/2-\delta L_*/4\ge p_*/4>0.
\tag{4}
\]
并且
\[
P(\gamma_0=1,M\in A_\delta)\longrightarrow p_*/2.
\tag{5}
\]

## 3. 固定b下严格的Ω(δ²)及构造的渐近系数

固定任意b>0，取
\[
0<\delta\le\min\{\delta_0,\,2\alpha b\},\qquad
\eta=\delta/(2\alpha).
\]
此时策略门控E正好是 \(\gamma_0=1,M\in A_\delta\)。结合01式(5)和(4)，
\[
J_{0,\delta}=\frac{\delta^2}{4A^2}P(E)
\ge\boxed{\frac{p_*}{16A^2}\delta^2}.
\tag{6}
\]
常数严格正且不依δ，攻击幅值在充分小δ时满足固定b。由(5)还得本构造的精确渐近系数
\[
\lim_{\delta\downarrow0}\frac{J_{0,\delta}}{\delta^2}
=\frac{p_*}{8A^2}.
\tag{7}
\]
这是此构造的系数，不是全策略最坏值的已知精确系数。K在式(7)消去，因为选择的η含1/|AK|；当A或K很小时，允许使用式(6)的δ范围也同时收缩，不能据此宣传任意系统巨大可行损伤。

## 4. 全策略上界与匹配阶数

明确记
\[
V_{m,\delta}^{(0)}(b,0)
=\sup_{\pi:\ |a_t|\le b,\ \Delta_\delta(\pi)=0}J_{0,\delta}(\pi),
\tag{8}
\]
策略类从t=0开始，无攻击前史；后续动作允许按原规则发生，但不能改变已经形成的t=0目标和t=1发送决定。目标固定为0，记录为 \((P_0^+,c_1,\gamma_1)\)。

上一轮 `01_scalar_feasibility_proof.md` 式(10)–(12)已证明：在共同b_ref、δ_ref范围内，Δ=0时
\[
J_{0,\delta}\le C_U\delta^2,\qquad
C_U=\left(\sqrt{c_0/q_*}+1/|A|\right)^2<\infty,
\tag{9}
\]
其中为避免符号歧义，本式c0是上一轮 \(\max_P1/[2V(P)]\) 常数，非本轮初始反馈值c_{0,δ}。q_*按固定b_ref、δ_ref选取，与实际变化的δ无关；P只遍历t=0的两个标签。

简要复核：令D为目标真条件均值与接收估计的差，e为下一量化误差，W=Y/s(P)。有 \(q_*E(D-e/A)^2\le1-E_\pi W\)。Δ=0使EπW=E0W，而健康基准的非零量化误差给 \(1-E_0W\le c_0\delta^2\)；再由L2三角不等式给(9)。P的期望差为零。未要求量化误差与D独立。

结合(6)和(9)，对任意固定 \(0<b\le b_{ref}\)，存在 \(\delta_*(b)>0\) 使全部0<δ≤δ*(b)满足
\[
\boxed{\frac{p_*}{16A^2}\delta^2
\le V_{m,\delta}^{(0)}(b,0)\le C_U\delta^2.}
\tag{10}
\]
即用户提出的 \(\Theta(\delta^2)\) **在本报告明确的标量、k=0、所选记录及无饱和量化协议下成立**。

这个“不可消除”含义是：对全部允许策略的零TV上界不可能统一改成o(δ²)。它不意味着每个攻击都有正损伤，更不意味着任何更丰富观测或防护都无法消除此风险。

## 5. 同一证明给出的b—δ联合边界

无需增加新策略族，取 \(\eta=\min\{b,\delta/(2\alpha)\}\)。安全门控集合包含Aδ，因此在0<δ≤min{δ0,δ_ref}时
\[
V_{m,\delta}^{(0)}(b,0)\ge\frac{p_*K^2}{4}
\min\{b^2,\delta^2/(4\alpha^2)\}.
\tag{11}
\]
又因为t=0之前没有攻击且发送决定不受当拍修改影响，一般允许策略在t=0的真实损伤就是 \(K^2E[\gamma_0a_0^2]\le K^2b^2\)。与(9)合并：
\[
V_{m,\delta}^{(0)}(b,0)\le\min\{K^2b^2,C_U\delta^2\}.
\tag{12}
\]
这说明损伤同时受攻击幅值与量化格宽限制。可在固定单位/模型常数下概括为 \(\Theta(\min\{b^2,\delta^2\})\)，但更准确的带量纲形式是(11)–(12)，尤其格内约束对应反馈坐标αb而非单纯b=δ。

式(11)是原任务同一构造的边界补充，不是原稿精确反馈双预算定理的整体量化版；本轮没有证明 \(\varepsilon>0\) 下的完整匹配公式或一般k版本。

## 6. 研究价值及不能据此认领的内容

数学上，δ²余量现在有同模型下的合法达到证据，不再仅是Young不等式保守项。原量化记录下的零正损伤性质确实失效，且最坏失效具有二次精度阶数。

但量化格内多对一、周期平均和范数平方都是标准机制；真正候选贡献是它们在既定可信随机反馈协议、合法因果攻击、指定联合记录与真实MSE目标下的完整边界。是否被已有量化隐蔽攻击结果直接覆盖，仍需全文排重；短证明本身既不证明缺乏价值，也不证明足够发表。
