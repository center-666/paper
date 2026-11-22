# 利用协方差度量证明任意事件历史的向量污染遗忘

本节不假设所有 \(F_t=(I-K_{\gamma,t}C)A\) 可交换，也不从单个矩阵特征值推断任意乘积稳定。采用随实际协方差变化的二次型度量，并给出可验证的共同包络。

## 1. 一般充分条件

记 \(R_0=R+Z^{-1},R_1=R\)（对p维整体触发可改为正定矩阵），
\[
\Psi_\gamma(P)=(P^{-1}+C^\top R_\gamma^{-1}C)^{-1}.
\]
Riccati映射在Loewner序下单调，且 \(\Psi_1(P)\preceq\Psi_0(P)\)。若存在 \(\overline P\succ0\) 满足
\[
Q\preceq P_0^-\preceq\overline P,\qquad
A\Psi_0(\overline P)A^\top+Q\preceq\overline P,
\tag{1}
\]
则归纳给所有允许事件历史
\[
Q\preceq P_t^-\preceq\overline P,\qquad
\underline\Lambda:=(Q^{-1}+C^\top R^{-1}C)^{-1}
\preceq P_t^+\preceq\overline\Lambda:=\Psi_0(\overline P).
\tag{2}
\]
这是一项可直接检验的矩阵不等式。可观测性/可检测性可帮助构造包络，但不代替对当前参数的(1)验证。静默仍有有限噪声虚拟观测，是本协议可以逐历史使用该包络的关键；不能照搬到完全丢失观测的丢包系统。

## 2. 每拍在变化的协方差范数中收缩

令 \(\Lambda_{t-1}=P_{t-1}^+\)、\(P_t^-=A\Lambda_{t-1}A^\top+Q\)、\(T_t=I-K_{\gamma,t}C\)。由于 \(T_t=P_t^+(P_t^-)^{-1}\)，
\[
F_t^\top(P_t^+)^{-1}F_t
=A^\top(P_t^-)^{-1}P_t^+(P_t^-)^{-1}A
\preceq A^\top(P_t^-)^{-1}A.
\]
若 \(Q\succeq qI,\overline P\preceq pI\)，\(0<q<p\)，则
\[
(P_t^-)^{-1/2}A\Lambda_{t-1}A^\top(P_t^-)^{-1/2}
=I-(P_t^-)^{-1/2}Q(P_t^-)^{-1/2}
\preceq(1-q/p)I.
\]
两个归一化矩阵乘积的非零奇异值相同，因此
\[
\boxed{F_t^\top(P_t^+)^{-1}F_t
\preceq\rho^2(P_{t-1}^+)^{-1},\qquad
\rho=\sqrt{1-q/p}<1.}
\tag{3}
\]
这是变化度量，不是找到了一个固定公共Lyapunov矩阵。沿真实协方差序列迭代后再用(2)比较范数，得
\[
\boxed{\|F_tF_{t-1}\cdots F_s\|_2
\le M\rho^{t-s+1},\quad
M=\sqrt{\lambda_{\max}(\overline\Lambda)/
\lambda_{\min}(\underline\Lambda)},\quad s\ge1.}
\tag{4}
\]
初始时刻P0是给定先验；(4)的s≥1保证每步先验来自前一后验的预测。不同起点都启动后的差分正是这种后验到后验传播。

## 3. 二维候选的精确有理数证书

对model.json指定的A,C,Q,R,Z,P0，取
\[
\overline P=\begin{pmatrix}.9&.1\\.1&.9\end{pmatrix}.
\]
它支配 \(P_0^-=.8I_2\)，最大特征值恰为1。直接计算
\[
\overline P-[A\Psi_0(\overline P)A^\top+Q]
=\begin{pmatrix}
5281/12500&-1499/50000\\
-1499/50000&14513/1600000
\end{pmatrix}\succ0,
\]
其首顺序主子式为5281/12500，行列式为11733429/4000000000，均严格正。又
\[
\underline\Lambda=\operatorname{diag}(1/25,1/20),\quad
\overline\Lambda=\begin{pmatrix}63/160&7/160\\7/160&143/160\end{pmatrix}\preceq I_2.
\]
因此可用简单保守常数
\[
\boxed{M=5,\qquad\rho=\sqrt{19/20}\approx0.9746794345.}
\tag{5}
\]
[certify_covariance.py](certify_covariance.py)以Fraction精确计算全部矩阵和主子式；该证书不依赖对有限事件历史的枚举。观测矩阵 \(\operatorname{col}(C,CA)\) 的行列式为1/10，两个开环特征值为1.02、.97：模型确有不稳定模态且仅直接观测第一状态。

## 4. 起点遗忘、有限总KL与污染包络

同幅值、不同起点候选在都已启动后输入相消，故
\[
\|\theta_t^{(1),+}-\theta_t^{(2),+}\|_2
\le M\rho^{t-s}\|\theta_s^{(1),+}-\theta_s^{(2),+}\|_2.
\]
同一历史下标量创新均值差为 \(-CA(\theta_{t-1}^{(1),+}-\theta_{t-1}^{(2),+})\)。相同当前幅值使两个核使用同一选择/平移通道，KL数据处理给
\[
\mathrm{KL}(K_{1,t}\Vert K_{2,t})
\le\frac{|CA(\theta_{t-1}^{(1),+}-\theta_{t-1}^{(2),+})|^2}{2S_t}.
\]
由S_t≥R和(4)，其起点之后尾和有限。前面有限拍的移动密度零点只造成可积log奇点，阶段四的有限性论证仍适用（状态偏差经C投影）。故固定同幅值起点对的全历史KL有限，仍不能让两类判别错误随单条历史增长同时趋零。

向量污染可由输入到状态界控制。发送时
\[
K_{1,t}^\top(P_t^+)^{-1}K_{1,t}
=\frac{CP_t^-C^\top}{R(CP_t^-C^\top+R)}\le1/R.
\]
用(3)及三角不等式，零初值、|b|≤bmax时
\[
\|\theta_t^+\|_{(P_t^+)^{-1}}
\le\frac{b_{\max}}{\sqrt R(1-\rho)}.
\tag{6}
\]
这给有限的统一欧氏/加权半径，常数可能很宽松。无需污染各分量非负；同时也不能保留标量的起点单调序、发送后正下界或2倍失效惩罚而不重证。

## 5. 失败情形与证明范围

若第二个不可观测模态改为1.01、且A为对角矩阵、C=(1,0)，其协方差会在该模态累积过程噪声，误差传播也有1.01模态；(1)的有界包络无法成立。这否定的是全状态任意向量乘积收缩；若特定攻击永远不能激励该模态，攻击可达子空间上仍可能有遗忘，不能从本反例直接推断其具体攻击历史必不遗忘。若Q只半正定，q可能为0，(3)不再给严格收缩，需要观测窗口/多步分析。

当前(5)是该二维参数的任意历史上界，不是最紧实际遗忘速度，也不是认证等待时间。四维/多传感器系统要重新验证(1)及其噪声、事件协议；未在本轮宣称自动通过。
