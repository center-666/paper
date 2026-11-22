# 多维状态、单量测的精确联合核与污染动力学

状态 \(x_t\in\mathbb R^n\)，量测 \(y_t=Cx_t+v_t\in\mathbb R\)。噪声独立高斯，\(Q\succ0,R>0\)，实际monitor预测为 \(m_t^-,P_t^-\)。反馈中心
\[
c_t=Q_{\delta,\phi_t}(Cm_t^-),\qquad r_t=c_t-Cm_t^-.
\]
仍在当前真实事件之后修改发送载荷：\(\widetilde y_t=y_t+\gamma_t a_t\)，其中 \(a_t=b\mathbf1_{\{t\ge k\}}\)。反馈中心/事件可信，原始载荷连续。以下条件化在同一已见接收历史及当前中心，不另生成健康反事实中心。

## 1. 高斯闭合与标量观测核

真实参数正确时，状态先验是 \(N(\mu_t^-,P_t^-)\)。令
\[
\theta_t^-=m_t^--\mu_t^-,\quad d_t=-C\theta_t^-,
\quad S_t=CP_t^-C^\top+R,\quad V_t=S_t+Z^{-1},
\quad u_t=\widetilde y_t-Cm_t^-.
\]
事件采用 \(\Pr(\gamma_t=0\mid y_t,c_t)=e^{-Z(y_t-c_t)^2/2}\)。静默原子和发送次密度依然为
\[
G_t=\frac{e^{-(d_t-r_t)^2/(2V_t)}}{\sqrt{1+ZS_t}},\qquad
f_t(u)=\phi_{S_t}(u-a_t-d_t)
\bigl[1-e^{-Z(u-a_t-r_t)^2/2}\bigr].
\tag{1}
\]
此处只要求量测维数为1，状态维数可以大于1。当前载荷修改不改变当前事件概率；过去污染通过d_t进入核。

发送且给定实际载荷后，已知候选参数可还原 \(y_t=\widetilde y_t-a_t\)，触发选择因子与状态无关，在状态后验归一化中抵消。静默时积分v_t后得到中心c_t、虚拟量测方差 \(R+Z^{-1}\) 的高斯似然。故
\[
K_{\gamma,t}=P_t^-C^\top(CP_t^-C^\top+R_\gamma)^{-1},\quad
R_1=R,\ R_0=R+Z^{-1},
\]
\[
P_t^+=(I-K_{\gamma,t}C)P_t^-,\qquad
P_{t+1}^-=AP_t^+A^\top+Q.
\tag{2}
\]
名义协方差标签依赖可信事件，仍与正确候选下条件协方差一致。若中心仅是隐藏相位的整数索引，上述多拍单高斯闭合不能直接沿用。

## 2. 向量污染及历史影响矩阵

从monitor与正确参数后验相减，得到
\[
\boxed{\theta_t^+=(I-K_{\gamma,t}C)\theta_t^-+
\gamma_tK_{1,t}b\mathbf1_{\{t\ge k\}},\qquad
\theta_{t+1}^-=A\theta_t^+.}
\tag{3}
\]
它不要求污染各分量非负。定义 \(H_{k,t}^+\in\mathbb R^{n\times1}\)，零初值后
\[
H_{k,t}^+=(I-K_{\gamma,t}C)A H_{k,t-1}^+
+\gamma_tK_{1,t}\mathbf1_{\{t\ge k\}},\qquad
\theta_t^+(k,b)=H_{k,t}^+b.
\tag{4}
\]
H只读事件、参数与协方差，仍不需要真实状态。若量测/攻击幅值维数为p，则H为n×p，线性关系仍成立。

## 3. 置信集合可以投影到向量，但不能逐分量照搬L

精确候选似然与正规化参考Q的反演覆盖不依赖状态是一维。取
\[
C_t^\varepsilon=\{\vartheta:p_{\vartheta,t}>\varepsilon q_t\},\qquad
\Theta_t=\{H_{k,t}^+b:\vartheta\in C_t^\varepsilon\},
\]
则对每个固定真参数，真实污染属于Θ_t的全时域概率至少 \(1-\varepsilon\)。污染方向未知时，不能把各坐标下界组成向量再直接相减；应使用03的凸包或方向支撑证书。

## 4. 单攻击幅值的强凹结构仍保留

固定k与历史，令 \(h_{k,i}=CAH_{k,i-1}^+\)（这是标量，允许变号），则d_i=−b h_{k,i}。阶段五的二次系数仍为
\[
B_{k,t}=\sum_{\gamma_i=1}(1-h_{k,i})^2/S_i+
\sum_{\gamma_i=0}h_{k,i}^2/V_i.
\]
起点后首次真实发送之前H仍为零，因此 \(B_{k,t}\ge1/S_{\max}\)。选择项仍为 \(\log h(u_i-r_i-b)\)，故每个移动零点分段上强凹性继续成立。关键是攻击幅值为单个标量；并非状态维数必须为1。

对方向性风险认证，固定方向d后低支撑候选约束是
\[
b\,d^\top W H_{k,t}^+\le z.
\tag{5}
\]
对每个k仍为一维线性幅值约束，只是系数可能正、负或零，必须相应改变保留区间。由此可复用阶段五的一维上包络思想；它不表示完整向量置信集合已经计算出来。
