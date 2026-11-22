# 一维亲和度积分及全域有界特征证书

## 1. 完成平方的积分式

两条件核共享S和实际中心残差r，发送密度为
\[
f_j(u)=\phi_S(u-a_j-d_j)h(u-a_j-r).
\]
记 \(m_j=a_j+d_j,\bar m=(m_1+m_2)/2\)，则
\[
\sqrt{\phi_S(u-m_1)\phi_S(u-m_2)}
=e^{-(m_1-m_2)^2/(8S)}\phi_S(u-\bar m).
\]
所以
\[
\mathcal A=\sqrt{G_1G_2}
+e^{-(m_1-m_2)^2/(8S)}
\mathbb E_{U\sim N(\bar m,S)}
\sqrt{h(U-a_1-r)h(U-a_2-r)}.
\tag{1}
\]
该一维表达式是精确恒等式，但普通数值求积和局部优化不是全参数域证书。用户提供的约0.0046缺口先保留为探索线索，本包不据此替换保证时间。

## 2. 另一条可认证路线：有界复特征

令观测统计量在静默时为0，发送时为
\(T_\omega=e^{i\omega(u-r)}\)，故 \(|T_\omega|\le1\)。取 \(z=d-r\)，高斯配方给
\[
F_\omega(S,z,a)=\mathbb E_{d,a}T_\omega
=e^{i\omega a}\left[
e^{-S\omega^2/2+i\omega z}
-G(z)e^{-\sigma^2\omega^2/2+i\omega z/(1+ZS)}
\right],
\]
\[
G(z)=\frac{e^{-z^2/(2(S+1/Z))}}{\sqrt{1+ZS}},\quad
\sigma^2=S/(1+ZS).
\tag{2}
\]
对任意两个概率核，
\[
|\mathbb E_1T-\mathbb E_2T|
\le\|\sqrt{K_1}-\sqrt{K_2}\|_2\|\sqrt{K_1}+\sqrt{K_2}\|_2
=2\sqrt{1-\mathcal A^2},
\]
因而
\[
1-\mathcal A\ge
\frac{|\mathbb E_1T-\mathbb E_2T|^2}{8}.
\tag{3}
\]
这给出不需要数值积分的充分分离证书。多个预先选定频率中任意一个满足下界都可认证当前参数箱；逐箱选不同频率只是确定性证明选择，不是数据后选择e-value。

## 3. 参数域与幅值平移消去

把观测载荷共同减去a_2，(2)的复相位公共因子抵消。特征差仅依赖
\[
S,\quad z_1=d_1-r,\quad z_2=d_2-r,\quad \Delta a=a_1-a_2.
\]
使用阶段四全历史包络 \(d_j\in[-AB_{\max},0]\)、\(|r|\le\delta_q\)，可扩大为独立的
\[
z_1,z_2\in[-AB_{\max}-\delta_q,\delta_q],\qquad
S\in[p_-+R,P_0+R].
\tag{4}
\]
这是覆盖真实合法域的矩形外包，放宽两z共用r的关联只使证书更保守。

本轮数值证书针对强攻击b=.25与有限字典中0、.05、.10的三个差值
\(\Delta a=.25,.20,.15\)，分别覆盖(4)的整个连续参数域。它不是对所有实数幅值间隔≥.15的直接认证，也不改变连续幅值理论的适用条件。有限字典保证只需这些三对核，故足以替换阶段四对应强档的统一上界。

## 4. 算术与全域覆盖证明

[certify_fourier.py](certify_fourier.py)用50位Decimal外向区间计算(2)–(3)。指数和平方根沿用阶段四正确舍入外扩合同；sin/cos用有限Taylor多项式及明确余项，区间以中点和Lipschitz半径向外扩。没有把NumPy优化结果当作上下界。

每个参数箱只在复特征差的模平方下端/8至少达到预定目标时接受；否则二分。穷尽所有未决箱才报告CERTIFIED；资源耗尽报告UNRESOLVED，不能使用部分覆盖作为全域证书。输出每个叶箱、二分路径、使用频率和认证缺口，以便复查整个根箱确被覆盖。

inspect_fourier.py的普通浮点局部搜索只作探索、排列频率的启发式不参与安全决策。全域结论完全来自区间端点、Taylor余项及完整二分树覆盖。算术保证依赖Decimal正确舍入契约，并非机器形式化定理证明。
