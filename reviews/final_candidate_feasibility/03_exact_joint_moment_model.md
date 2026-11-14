# 03 缓存、估计误差、隐私噪声与FDI的完整联合矩

日期：2026-11-14。以下均为DERIVED / STANDARD，不是新增算法。采用02号固定日程、确定增益；标量a可替换为矩阵A。

## 1. 同一包的隐私轨迹

固定接收时刻τ和年龄0至m：

\[
L_m=\operatorname{col}(1,a,\ldots,a^m),\quad
\eta=L_m\xi_\tau,\quad \mu_\xi=\mathbb E\xi_\tau.
\]

精确有

\[
\mathbb E\eta=L_m\mu_\xi,\quad
\operatorname{Cov}(\eta)=L_m\Sigma_\xi L_m^T,
\quad
\mathbb E[\eta\eta^T]=L_m(\Sigma_\xi+\mu_\xi^2)L_m^T.
\tag{M1}
\]

矩阵版 \(L_m=\operatorname{col}(I,A,\ldots,A^m)\)。隐私子块秩至多状态维数，不意味着总残差奇异。若均值未知且无界，协方差界不足以控制原始二阶风险。条件化于载荷历史后应换成相应条件均值/协方差，不能沿用无条件分布。

## 2. 缓存对真状态的误差

令 \(s_\tau=x_\tau-\hat x_{j,\tau}\)，缓存年龄记为ℓ：

\[
W_\ell=\sum_{t=0}^{\ell-1}a^{\ell-1-t}w_{\tau+t},
\quad g_\ell=a^\ell s_\tau+W_\ell.
\]

则

\[
f_\ell=x_{\tau+\ell}-a^\ell q_{ji,\tau}
=g_\ell-a^\ell\xi_\tau-a^\ell\delta_\tau.
\tag{M2}
\]

均值为

\[
\mu_f=\mu_g-a^\ell\mu_\xi-a^\ell\mu_\delta.
\tag{M3}
\]

用 \(M_{uv}=\mathbb E[uv]\) 表示原始交叉矩：

\[
\mathbb E[f_\ell^2]=M_{gg}
+a^{2\ell}(M_{\xi\xi}+M_{\delta\delta}+2M_{\xi\delta})
-2a^\ell(M_{g\xi}+M_{g\delta}),
\tag{M4}
\]

\[
\mathbb E[ef_\ell]=M_{eg}-a^\ell M_{e\xi}-a^\ell M_{e\delta},
\qquad e=x-\hat x_i.
\tag{M5}
\]

没有删除噪声、攻击、估计误差间的任何交叉项。由
\(M_{uv}=\operatorname{Cov}(u,v)+\mu_u\mu_v\)
恢复中心协方差和偏置项。

堆叠 \(f=g-L\xi-L\delta\) 的矩阵式：

\[
\begin{aligned}
M_f={}&M_g+L(M_{\xi\xi}+M_{\delta\delta}
+M_{\xi\delta}+M_{\delta\xi})L^T\\
&-M_{g\xi}L^T-LM_{\xi g}
-M_{g\delta}L^T-LM_{\delta g}.
\end{aligned}
\tag{M6}
\]

矩阵交叉块不能省略转置顺序。完整残差若还含本地量测、过程噪声、反馈误差，必须全部增广，不能用隐私子块代替总矩。

## 3. 两节点反馈下的精确递推

令 \(c_{ji,k}=x_k-c_{ji,k}^{\rm value}\) 为当拍接收后的缓存误差。由Yang更新：

\[
e_{i,k+1}=(a-K_{i,k}h_i-\epsilon a)e_{i,k}
+\epsilon a c_{ji,k}+w_k-K_{i,k}v_{i,k}.
\tag{M7}
\]

先预测缓存：

\[
c^-_{ji,k+1}=a c_{ji,k}+w_k.
\tag{M8}
\]

下一拍若接收新包：

\[
c^+_{ji,k+1}=e_{j,k+1}-\xi_{ji,k+1}-\delta_{ji,k+1};
\tag{M9}
\]

否则 \(c^+=c^-\)。另一个方向同理。同一个w同时进入两节点误差和缓存误差，不能按独立副本处理。

增广 \(z_k^+=\operatorname{col}(e_1,e_2,c_{21},c_{12})\)，日程决定接收重置R，模型及增益决定F：

\[
z_{k+1}^-=F_kz_k^++G_k\nu_k,\quad
z_{k+1}^+=R_{k+1}z_{k+1}^-+D_{k+1}u_{k+1}.
\tag{M10}
\]

ν含共同w及本地v；u含新包ξ/δ，D含负号。F估计行来自M7，缓存行来自M8；R在接收缓存行复制发送节点当前误差，其他行保持。有限时域因此是基础变量ζ的确定线性映射：

\[
z_k=T_k\zeta,\quad \mu_{z_k}=T_k\mu_\zeta,\quad
M_{z_k}=T_kM_\zeta T_k^T.
\tag{M11}
\]

若写成 \(z'=Bz+Du\)，必须保留

\[
M_{z'}=BM_zB^T+DM_uD^T+BM_{zu}D^T+DM_{uz}B^T.
\tag{M12}
\]

这是标准增广理论，不需要读取未发送估计实现值；但需要有效基础矩/集合。知道F不等于知道 \(M_\zeta\)。不重复运行G1-R传播验证。

## 4. 隐私不确定集合和有界攻击

若机制认证中心化与协方差区间，取

\[
\mu_\xi=0,\qquad 0\le\underline s\le M_{\xi\xi}\le\bar s<\infty.
\tag{M13}
\]

该条件由机制或独立包统计支持，不由缓存重复支持。若均值仅知 \(|\mu_\xi|\le m\)，原始矩上界须用 \(\bar s+m^2\)。

攻击条件取 \(|\delta|\le b\)，故 \(M_{\delta\delta}\le b^2\)。允许非零均值、随机化、依赖攻击者已见载荷及与ξ/误差相关。对有限ζ可用标准矩外包

\[
\mathscr M=\left\{(\mu,M):
\begin{bmatrix}M&\mu\\\mu^T&1\end{bmatrix}\succeq0,\
M_{ll}\le B_l,\
\underline s\le M_{\xi\xi}\le\bar s,\
\mu_\xi=0,\
\text{其他已认证矩约束}\right\}.
\tag{M14}
\]

多包/二维用对应块约束。硬幅值的完整分布条件强于二阶矩限制，因此M14是保守外包，不声称每个PSD点都是实际因果攻击可达点。

任意已知行t上有

\[
\sup_{\mathscr M}tMt^T
\le\left(\sum_l|t_l|\sqrt{B_l}\right)^2<\infty.
\tag{M15}
\]

由Cauchy–Schwarz即可证明；仅有边际矩时该包络可取到等号。同一ξ重复使用应先合并系数，不当作新独立变量。更细矩约束下求支持函数是标准凸矩优化，不在本轮编写求解器。

由M2直接得到

\[
\mathbb E[f_\ell^2]\le
\left(|a|^\ell\sqrt{\bar S}+\sqrt{\bar W_\ell}
+|a|^\ell\sqrt{\bar s}+|a|^\ell b\right)^2.
\tag{M16}
\]

\(\bar S\)必须控制发送端实际受攻误差；\(\bar W_\ell\)由过程噪声矩与相关信息构造。只有边际界时用三角界，已知白噪声规则时可用准确卷积矩。有限界不意味着比CI更紧。接收端自身的P也必须包含过去攻击反馈影响，不能用健康P冒充。

## 5. 完整矩到当前和下一拍融合风险

两份估计误差为e、f，记 \(p=M_{ee},r=M_{ff},c=M_{ef}\)。确定权重下：

\[
J(\lambda)=(1-\lambda)^2p+\lambda^2r+2\lambda(1-\lambda)c.
\tag{M17}
\]

均值项已包含在原始矩内。

为严格对应Yang下一拍，选两份在线可计算候选：

\[
U=a\hat x_i+K_i(y_i-h_i\hat x_i),\quad
V=a q_{ji}^{\rm aligned}+K_i(y_i-h_i\hat x_i).
\tag{M18}
\]

\((1-\lambda)U+\lambda V\)正是把I3边系数ε替为λ的同一位置。真实误差：

\[
e_U=(a-K_ih_i)e_i+w-K_iv_i,\quad
e_V=a c_{ji}-K_ih_i e_i+w-K_iv_i.
\tag{M19}
\]

它们共享创新噪声及旧误差，不独立。把M11系数行换成M19即可计算矩/界，04号比较可直接用于此接口，不偷偷更换滤波器。

## 6. 证明边界

- M1—M12、M17—M19是精确恒等式，不用误差独立假设。
- M13—M16依赖合法有效基础矩界及攻击界，是标准有限时域总体风险上界。
- 未证明这些输入能由当前单条载荷自动获得，也未将无条件矩当作每条在线记录的条件矩。
- 未证明任意不稳定a、无限长缓存或持续无界攻击的统一稳定性。没有运行任何新仿真或算法。
