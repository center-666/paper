# 全部允许因果策略的窗口损伤上界

**DERIVED / PASS。** 本文完整重述并独立核验旧 [theorem_audit.md](../theorem_audit.md) §§1–6 的结论，不认领本轮新定理。

## 1. 模型、信息与量词

固定维数 \(n,p\ge1\)、整数 \(k\ge0,L\ge1\)、\(b_{\rm ref}>0\)，以及
\[
x_{t+1}=Ax_t+w_t,\qquad y_t=Cx_t+v_t,
\]
其中
\[
x_0\sim N(m_0,P_0),\quad w_t\sim N(0,Q),\quad v_t\sim N(0,R),\qquad
m_0^-=m_0,\quad P_0^-=P_0,
\]
\(P_0>0,Q>0,R>0,Z>0\)，初态、全部过程与测量噪声、独立 \(U_t\sim{\rm Unif}[0,1]\) 和私有随机种子 \(S\) 彼此独立。初态均值 \(m_0\) 已知。物理状态不受接收估计的控制输入影响；无丢包、延时或事件伪造。结论不要求 \(A\) 可逆或稳定。

实际预测 \(m_t^-\) 可信反馈给触发器，事件先于载荷修改：
\[
\gamma_t=0\iff U_t\le g(y_t-Cm_t^-),\qquad
g(r)=e^{-r^\top Zr/2}.
\]
在 \(\gamma_t=1\) 后才将 \(y_t\) 改为 \(y_t+a_t\)。静默时 \(a_t=0\)。

写 \(Y_t^{\rm true}=y_t\)（发送时），否则为 \(\bot\)，定义
\[
\mathcal G_t^-=\sigma(S,\gamma_{0:t-1},Y_{0:t-1}^{\rm true}),\quad
\mathcal G_t^+=\mathcal G_t^-\vee\sigma(\gamma_t,Y_t^{\rm true}).
\]
所有合法策略允许任意 \(\mathcal G_t^+\)-可测、量测相关、非线性、随机动作，逐路径 \(\|a_t\|\le b\le b_{\rm ref}\)。攻击者无静默量测、隐藏状态或未来随机数。固定策略后，接收均值与已实施动作都由该历史重建。

令 \(R_1=R,R_0=R+Z^{-1}\)，
\[
K_i(P)=PC^\top(CPC^\top+R_i)^{-1},\quad
M_i(P)=I-K_i(P)C,\quad
F_i(P)=P-PC^\top(CPC^\top+R_i)^{-1}CP.
\]
接收器执行
\[
m_t^+=m_t^-+\gamma_tK_1(P_t^-)(y_t+a_t-Cm_t^-),\quad
P_t^+=F_{\gamma_t}(P_t^-),
\]
\[
m_{t+1}^-=Am_t^+,\qquad P_{t+1}^-=AP_t^+A^\top+Q.
\]
静默时接收均值不动，但条件真实均值不一定不动。

定义
\[
E_L=\{\gamma_{k+1}=\cdots=\gamma_{k+L}=0\},\quad
R_L=(P_k^+,Y_L),\quad Y_L=1_{E_L},
\]
\[
\Delta_L(\pi)={\rm TV}(\mathcal L_\pi(R_L),\mathcal L_0(R_L)),\quad
{\rm TV}(\mu,\nu)=\sup_B|\mu(B)-\nu(B)|,
\]
\[
J_k(\pi)=E_\pi\|x_k-m_k^+\|^2-E_0\|x_k-m_k^+\|^2.
\]
两项期望使用各自实际协议；不冻结健康事件轨迹。审计记录不含连续载荷或内部预测。更丰富且可投影到 \(R_L\) 的记录可用数据处理得到同系数上界。

## 2. 条件 Gaussian 与偏差递推

设 \(\mu_t^\pm=E_\pi[x_t\mid\mathcal G_t^\pm]\)。归纳证明
\[
x_t\mid\mathcal G_t^\pm\sim N(\mu_t^\pm,P_t^\pm).
\tag{1}
\]
初态成立，因为 \(S\) 独立。发送时给定真实 \(y_t\)，似然中的 \(1-g(y_t-Cm_t^-)\) 与 \(x_t\) 无关而消去；后验为通常测量更新。静默时积分未发送测量：
\[
\Pr(\gamma_t=0\mid x_t,\mathcal G_t^-)
=\det(I+RZ)^{-1/2}
\exp[-(Cx_t-Cm_t^-)^\top(R+Z^{-1})^{-1}(Cx_t-Cm_t^-)/2].
\]
因此
\[
\mu_t^+=
\begin{cases}
\mu_t^-+K_1(P_t^-)(y_t-C\mu_t^-),&\gamma_t=1,\\
\mu_t^-+K_0(P_t^-)(Cm_t^--C\mu_t^-),&\gamma_t=0.
\end{cases}
\]
协方差均为 \(F_{\gamma_t}(P_t^-)\)；预测使用独立过程噪声。给定真实发送历史后攻击动作已知，故非线性动作不破坏该归纳。这不是宣称受攻载荷日志下后验 Gaussian，也不是宣称发送条件下尚未观测的 \(y_t\) Gaussian。

令 \(D_t=\mu_t^+-m_t^+\)，\(d_t=\mu_t^--m_t^-\)。则
\[
D_t=M_{\gamma_t}(P_t^-)d_t-\gamma_tK_1(P_t^-)a_t,\quad
d_{t+1}=AD_t,\quad d_0=0.
\tag{2}
\]
条件正交性消去 \(E[(x_k-\mu_k^+)^\top D_k]\)，健康时 \(D=0\)，于是
\[
J_k=E_\pi\|D_k\|^2+
E_\pi{\rm tr}P_k^+-E_0{\rm tr}P_k^+.
\tag{3}
\]
有限时域、峰值动作与 Gaussian 二阶矩保证相关期望有限。第二项不可省略。

## 3. 事件历史外包与统一幅值

令 \(h=\gamma_{0:k}\in\{0,1\}^{k+1}\)。\(P_t^\pm(h)\)、所有增益只由事件串决定，连续真实量测仍无限多。定义
\[
T_t(h)=M_{h_t}(P_t^-(h))A,\quad
\Phi_{k,t}(h)=T_k(h)\cdots T_{t+1}(h),\quad \Phi_{k,k}=I,
\]
\[
B_{k,h}=[-\Phi_{k,t}(h)K_1(P_t^-(h)):h_t=1],\quad
\mathcal R_{k,h}={\rm range}B_{k,h}.
\]
由 (2)，所有实际路径满足
\[
D_k=B_{k,h}\,{\rm col}(a_t:h_t=1)\in\mathcal R_{k,h},\quad
\|D_k\|\le B_*,
\]
\[
B_*=b_{\rm ref}\max_h\sum_{t:h_t=1}
\|\Phi_{k,t}(h)K_1(P_t^-(h))\|_2<\infty.
\tag{4}
\]
这仅是外包；充分证明不需要证明预算盒的所有像能由同一个因果策略同时实现。

## 4. 联合静默积分与记录函数

给定 \(\mathcal G_k^+\)，在假定未来全静默路径上接收均值为 \(A^jm_k^+\)。在尚未按未来事件筛选的物理输出上，
\[
r=G_LD_k+\eta,\qquad G_L={\rm col}(CA,\ldots,CA^L),
\]
\[
[V_L(P)]_{ij}
=C\left(A^iP(A^j)^\top+
\sum_{q=1}^{\min(i,j)}A^{i-q}Q(A^{j-q})^\top\right)C^\top+R1_{i=j}.
\]
独立未来 \(U\) 给乘积触发概率，再对联合 Gaussian 积分。设 \(\bar Z=I_L\otimes Z\)，则
\[
s_L(P)=\det(I+\bar Z^{1/2}V_L(P)\bar Z^{1/2})^{-1/2}>0,\quad
H_L(P)=\tfrac12G_L^\top[V_L(P)+\bar Z^{-1}]^{-1}G_L,
\]
\[
\Pr_\pi(E_L\mid\mathcal G_k^+)
=s_L(P_k^+)e^{-D_k^\top H_L(P_k^+)D_k},\quad
\ker H_L(P)=\ker G_L.
\tag{5}
\]
允许目标后仍有攻击；全静默分支没有可改载荷，因此不影响 (5)。不能将 (5) 解读为条件于未来全静默后输出仍具有原协方差 \(V_L\)。

## 5. 定理与完整闭合

假定对每个 \(h\)
\[
\ker G_L\cap\mathcal R_{k,h}=\{0\}.
\tag{6}
\]
对非零 \(\mathcal R_{k,h}\) 取正交基 \(U_h\)，有限历史和 (6) 给
\[
\lambda_*=\min_{\mathcal R_{k,h}\ne0}
\lambda_{\min}(U_h^\top H_L(P_k^+(h))U_h)>0.
\]
定义
\[
q_*=\frac{1-e^{-\lambda_*B_*^2}}{B_*^2},\quad
M_*=\max_h s_L(P_k^+(h))^{-1},\quad
\Omega_k=\max_h{\rm tr}P_k^+(h)-\min_h{\rm tr}P_k^+(h).
\tag{7}
\]
凹函数割线界在 \(0\le\|D_k\|^2\le B_*^2\) 上给
\[
q_*\|D_k\|^2\le1-e^{-D_k^\top H_L(P_k^+)D_k}.
\tag{8}
\]
使用同一个可观测函数 \(f(P,Y)=Y/s_L(P)\in[0,M_*]\)，由 (5)
\[
E_0f=1,\quad E_\pi f=E_\pi e^{-D_k^\top H_L(P_k^+)D_k}.
\]
因此
\[
q_*E_\pi\|D_k\|^2
\le E_0f-E_\pi f\le M_*\Delta_L.
\tag{9}
\]
该 TV 系数是取值跨度 \(M_*\)，不是 \(2M_*\)。不存在将条件 TV 的平均错当整体 TV 的步骤。即使多个历史共用同一 \(P\)，归一化函数仍然有效。

标签是记录的投影，故
\[
|E_\pi{\rm tr}P_k^+-E_0{\rm tr}P_k^+|\le\Omega_k\Delta_L.
\tag{10}
\]
由 (3)、(9)、(10)，对全部合法策略以及全部 \(0\le b\le b_{\rm ref}\)：
\[
\boxed{J_k(\pi)\le C_{k,L}\Delta_L(\pi),\qquad
C_{k,L}=M_*/q_*+\Omega_k<\infty.}
\tag{11}
\]
若全部 \(\mathcal R_{k,h}=\{0\}\)，则 \(D_k=0\)，直接取 \(C_{k,L}=\Omega_k\)，不用空集谱最小值。

常数仅依赖固定 \(A,C,P_0,Q,R,Z,k,L,b_{\rm ref}\)，与策略、数值历史、种子及实际 \(b\) 无关。它不是长时间统一界或有限样本检测算法。静默稀少会使 \(M_*\) 大，近核方向会使 \(\lambda_*\) 小；数学有限不等于数值紧。

## 6. 零预算的结论

由 \(\Delta_L=0\) 得 \(D_k=0\) 几乎处处，且标签同律，故 \(J_k=0\)。满列秩 \(G_L\) 是 (6) 的充分特例；条件 (6) 自身不是该结论的必要条件，见下一份报告。
