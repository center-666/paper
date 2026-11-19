# 连续静默窗口的联合 Gaussian 推导

## 条件路径

固定目标时刻的完整受限历史 \(\mathcal G_k^+\)，令

\[
D_k=\mathbb E[x_k\mid\mathcal G_k^+]-m_k^+,
\qquad P=\operatorname{Cov}(x_k\mid\mathcal G_k^+).
\]

在未来 \(L\) 拍全部静默时，接收均值递推为 \(m_{k+j}^-=A^jm_k^+\)。定义未来创新堆叠

\[
r_j=y_{k+j}-Cm_{k+j}^-,
\qquad r=\operatorname{col}(r_1,\ldots,r_L).
\]

由状态递推，

\[
r=G_LD_k+\eta_L,
\qquad G_L=\operatorname{col}(CA,CA^2,\ldots,CA^L),
\]

其中 \(\eta_L\) 为零均值 Gaussian。其块协方差为

\[
[V_L(P)]_{ij}=C\left(A^iP(A^j)^\top+
\sum_{q=1}^{\min(i,j)}A^{i-q}Q(A^{j-q})^\top\right)C^\top+R\,1_{i=j}.
\]

这里的过程噪声相关性不能删去；未来创新不是一般意义上的独立同分布样本。

## 联合静默概率

若每一拍事件使用独立触发随机数并以 \(\exp(-r_j^\top Zr_j/2)\) 产生静默，则条件于 \(\mathcal G_k^+\) 的整段静默概率是

\[
\begin{aligned}
s_L(P)&=\det(I+V_L(P)(I_L\otimes Z))^{-1/2},\\
H_L(P)&=\frac12G_L^\top\left[V_L(P)+(I_L\otimes Z)^{-1}\right]^{-1}G_L,\\
\Pr(E_L\mid\mathcal G_k^+)&=s_L(P)\exp[-D_k^\top H_L(P)D_k].
\end{aligned}
\]

DERIVED：这是对联合 Gaussian 密度乘以块对角触发权重后完成平方和积分的结果。它要求精确实际预测、未来窗口中没有发送载荷可被修改，以及触发随机数独立。若传感器使用其他中心、量化中心或相关触发随机数，公式不能直接搬用。

## 正定性

因 \(V_L(P)+(I_L\otimes Z)^{-1}>0\)，有

\[
\ker H_L(P)=\ker G_L,
\qquad H_L(P)\succ0\Longleftrightarrow \operatorname{rank}G_L=n.
\]

这是标准有限时域可观测性事实。它说明整段事件比单个事件可能包含更多方向信息，但本身不说明攻击者能够产生这些方向。

## 可用于安全上界的条件

固定有限 \(k,L\) 和每个目标前历史 \(h\)。令 \(\mathcal A_{k,h}\) 表示在该历史、真实发送机会、Kalman 增益和峰值约束下实际可达的目标偏差集合，令 \(\mathcal R_{k,h}=\operatorname{span}(\mathcal A_{k,h})\)。若

\[
\ker G_L\cap\mathcal R_{k,h}=\{0\}
\]

对所有有非零可达空间的有限历史成立，则有限历史数目给出

\[
h_*=
\min_h\lambda_{\min}\bigl(U_h^\top H_L(P(h))U_h\bigr)>0,
\]

其中 \(U_h\) 是 \(\mathcal R_{k,h}\) 的正交基。若 \(\|D_k\|\le B_*\)，则

\[
1-e^{-D_k^\top H_L(P)D_k}
\ge
\frac{1-e^{-h_*B_*^2}}{B_*^2}\|D_k\|^2.
\]

结合静默事件概率的有限正下界和协方差标签的有限历史差异，可得到固定 \(k,L\) 的 \(J_k\le C_{k,L}\,\mathrm{TV}(\mathcal L_\pi(P_k^+,Y_L),\mathcal L_0(P_k^+,Y_L))\) 型界。这里 \(Y_L=1_{E_L}\) 或完整未来事件串；常数依赖模型、\(k,L\) 和峰值上界，不能写成无限时域统一常数。

该段是 CONDITIONAL/DERIVED：完整证明还需把历史标签、协方差差异和记录定义逐项接上；不能只凭 \(G_L\) 满秩宣布全策略定理。
