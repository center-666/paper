# 03 可辨识、信息与Replay统计边界

日期：2026-11-14。DERIVED表示本轮推导，不表示创新；传播、GLS、功能可辨识、Schur和conformal均是标准工具。

## 1. 已知事件的目标可辨识

无噪声响应g=Oθ，目标Gθ可唯一确定，当且仅当

\[
\ker O\subseteq\ker G
\iff \exists L:G=LO
\iff \operatorname{rank}\begin{bmatrix}O\\G\end{bmatrix}
=\operatorname{rank}O.
\tag{T1}
\]

证明：两个相同观测解释之差在kerO，目标相同等价于其在kerG。在range(O)定义L(Oθ)=Gθ，核包含保证良定义，随后可线性延拓；行空间形式给出秩式。

未知目标方向数：

\[
\dim G(\ker O)=
\operatorname{rank}\begin{bmatrix}O\\G\end{bmatrix}-\operatorname{rank}O.
\tag{T2}
\]

这是结构条件，不保证有限噪声下精确恢复或数值稳定。真正两阶段方向互补至少要求

\[
\operatorname{rank}O_J>
\max(\operatorname{rank}O_C,\operatorname{rank}O_P),
\tag{T3}
\]

或联合满足T1、两个单阶段均不满足。P已满秩而J仅比C增秩，不构成联合不可替代性。

## 2. 实际模型的解析障碍

原包驻留时

\[
O_C=\operatorname{col}_{a=0}^{q-r-1}(-H_iA^a).
\tag{T4}
\]

主模型每个H_i满列秩，第一块已rank2，所以

\[
\operatorname{rank}O_C=2,\quad\ker O_C=\{0\},\quad
\operatorname{rank}O_J\le2.
\tag{T5}
\]

**PROVED：主模型没有新增攻击参数方向的空间。** 与seed、幅值和Replay年龄无关；不否定精度、条件数或未知事件区分收益。

秩亏模型中，测x1节点有[1,0]及[1,0.1]，两拍即rank2；测x2节点有[0,1.01^a]，C始终rank1。P能否借其他节点反馈补足需算实际响应，不能用示意矩阵作证。

## 3. 联合信息与Schur分解

确定θ、健康Gaussian位置族、Σ正定时：

\[
g=\begin{bmatrix}O_C\\O_P\end{bmatrix}\theta+\eta,\quad
\Sigma=\begin{bmatrix}\Sigma_{CC}&\Sigma_{CP}\\
\Sigma_{PC}&\Sigma_{PP}\end{bmatrix}.
\]

令

\[
S=\Sigma_{PP}-\Sigma_{PC}\Sigma_{CC}^{-1}\Sigma_{CP},\quad
\widetilde O_P=O_P-\Sigma_{PC}\Sigma_{CC}^{-1}O_C,
\]

块三角白化给

\[
\mathcal I_J=\mathcal I_C+\widetilde O_P^TS^{-1}\widetilde O_P.
\tag{T6}
\]

后项半正定，不等于增加新方向。C满秩后仍只改善原空间精度。对P有对称分解。数值同时给原始/白化O的秩、奇异值、信息特征值和Schur误差；未白化奇异值随单位改变，不单独解释为性能。不用ridge制造满秩。

## 4. 两残差关系与强基线

同一拍同一边有

\[
g_C(k)=g_P(k)+H_i(\hat x_i(k)-A^{age(k)}q_e).
\tag{T7}
\]

都可从合法本地记录重构，不增加协议字段。但差值是随机缓存分歧，不能据此说旧“仅innovation数组”已充分。

公平强基线须允许同样逐边缓存、估计历史做标准多通道full-prefix GLS。旧full_prefix_cache只加了入边分歧之和，不自动等于全部逐边特征。联合窗口比post-cache多用量测，精度收益可能只是样本数与标准联合处理；未与同风险OR比较前不能宣称优势。本轮不做性能试验。

## 5. 未知事件的独立判据

在同一合法观测空间，令 \(\mathcal O_{h,\ell}=[O_h,-O_\ell]\)，
两事件h、ℓ不可区分解释满足
\(\mathcal O_{h,\ell}\operatorname{col}(\theta_h,\theta_\ell)=0\)。
目标影响可区分的条件是

\[
\ker[O_h,-O_\ell]\subseteq\ker[G_h,-G_\ell].
\tag{T8}
\]

可查未辨识目标方向数、子空间交和主角。只有两个阶段各自不行而联合可行，才有该对事件的联合结构收益。仅主角变大不是新增可辨识对。

各候选若换窗口/缓存，不能直接比较列空间。本轮45对采用同一固定节点1观测坐标；不把其他接收节点私有数据当全网可见。

## 6. Replay、GLS协方差和Fisher

固定合法源s的单次Replay：
\(\theta=\hat x_j^0(s)-\hat x_j^0(r)\)，一般与健康η相关。逐样本g=Oθ+η仍成立。联合Gaussian时，在θ支持上

\[
\mathbb E[g\mid\theta]
=(O+C_{\eta\theta}\Sigma_\theta^\dagger)\theta,
\]

\[
\operatorname{Cov}(g\mid\theta)
=\Sigma_\eta-C_{\eta\theta}\Sigma_\theta^\dagger C_{\theta\eta}.
\tag{T9}
\]

非零均值须中心化；数据依赖选源还可能非Gaussian。因此 \(O^T\Sigma_{\rm healthy}^{-1}O\) 对确定外生FDI是位置族Fisher，对Replay只称GLS设计信息/白化响应几何，不能直接推非中心χ²功效或后验置信度。

但已知事件且KO=I时

\[
\hat\theta-\theta=K\eta,\quad
\mathbb E[(\hat\theta-\theta)(\hat\theta-\theta)^T]
=K\Sigma_\eta K^T
\tag{T10}
\]

在η零均值时仍成立，不需θ与η独立。只估目标时LO=G同理。这是无条件误差矩，不是给定θ、观测或经过报警/事件选择后的条件后验。

## 7. 幅值、误报与恢复边界

强/half/low共用O和Σ，幅值乘c使确定方向的 \(\theta^T\mathcal I\theta\) 乘c²，不改秩。低幅检出困难是功效，不是结构方向消失。Replay同样不改给定h的响应，统计解释按T9。

轨迹最大值split-conformal需预先冻结评分及正常轨迹交换性，不保证定位正确或分布变化后仍覆盖；本轮不实现。

设 \(e^0=x-\hat x^0,\Delta=\hat x^a-\hat x^0,u=\Delta-\hat\Delta\)，恢复MSE差应区分：

\[
J_c-J_0=\mathbb E\|u\|^2-2\mathbb E[(e^0)^Tu],
\]

\[
J_c-J_a=\mathbb E\|u\|^2-\mathbb E\|\Delta\|^2
-2\mathbb E[(e^0)^Tu]+2\mathbb E[(e^0)^T\Delta].
\tag{T11}
\]

附件第一式是相对健康轨迹，不是直接相对受攻击轨迹。影响估计协方差小和阈值通过都不自动保证真实MSE改善，当前不开发修正门控。
