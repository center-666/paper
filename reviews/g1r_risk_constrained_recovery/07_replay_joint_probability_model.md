# 07 Replay参数与本地创新的联合Gaussian模型

日期：2026-11-14。任务2交付；协议[06](06_experiment_preregistration.md)和[机器配置](protocol_v1.json)在数值输出前冻结。所有DERIVED结论是本轮推导，不自动构成原创理论。

## 1. 随机对象、合法信息和时间点

固定外生日程、原Yang名义增益及单次载荷替换。初态x0~N(0,P0)，w_t~N(0,Q)、v_i(t)~N(0,R_i)，跨时间、节点及初态独立；物理过程和本地量测不受攻击。所有初始估计为0，t=0各节点发送。系统和增益不改，攻击不改变发送日程。

给定h=(e=(j,1),r)和预先固定年龄a，s=r−a必须为真实发送时刻，替换载荷为**原始历史发送估计hat x_j^0(s)**，不是A^a hat x_j^0(s)。因此

\[
\theta_{h,a}=\hat x_j^0(s)-\hat x_j^0(r).
\tag{1}
\]

r之前无攻击，故式(1)等于实际单枚Replay造成的载荷差。正文统计模型把h和a视为固定或独立于Gaussian原始噪声的离散抽样；若按已观察载荷自适应选源，条件分布可能非Gaussian，不能沿用下述Bayes模型。

部署端只得到z=col(nu_1(211),...,nu_1(216))。O_h、G_h从既有固定日程传播资产提取，目标为217；未重新执行攻击传播验证。逐样本有

\[
z=\eta^0+O_h\theta_{h,a},\quad
\Delta_{217}=G_h\theta_{h,a},\quad
e^a=e^0+\Delta_{217},
\tag{2}
\]

其中e0=hat x_1^0(217)−x217。eta^0是同初态、过程和量测噪声的健康反事实创新。式(2)不需要theta与eta^0独立。

## 2. 精确健康增广状态，不使用瞬时通信报告协方差

定义真实减估计误差epsilon_i=x−hat x_i^0、对齐缓存误差b_e=x−A^{age_e}q_e^0，增广状态

\[
X_k=\operatorname{col}(x_k,\epsilon_0(k),...,\epsilon_4(k),b_0(k),...,b_9(k))\in R^{32}.
\tag{3}
\]

用−/+区分收包前后。收包重置S_k保留x/epsilon，并在sender j发送时令b_{ji,k}^+=epsilon_j(k)；静默边保留其预测缓存误差。随后

\[
\begin{aligned}
x_{k+1}&=Ax_k+w_k,\\
\epsilon_{i,k+1}
&=[(1-\varepsilon\deg_i)A-K_i(k)H_i]\epsilon_{i,k}
+\varepsilon A\sum_{e\to i}b_{e,k}^++w_k-K_i(k)v_i(k),\\
b_{e,k+1}^-&=Ab_{e,k}^++w_k.
\end{aligned}
\tag{4}
\]

这是既有误差递推加物理x，不是新的攻击传播定理。共同w同时进入所有节点/缓存，不能拆成独立过程噪声。同拍v进入创新和未来epsilon，不能遗漏交叉相关。初态中所有epsilon和b都等于x0，协方差不是块独立。

令F_k、B_w、B_v为式(4)矩阵，则

\[
X_k^+=S_kX_k^-,\qquad
X_{k+1}^-=F_kX_k^++B_ww_k+B_vv_k.
\tag{5}
\]

传输只改变缓存行；当前节点epsilon不因当拍收包立刻改变，age0包经当拍一致性项影响下一状态。故O使用211—216，G使用217，均符合原实现时序。

## 3. 原始独立噪声的确定性系数表示

引入概念上的独立标准Gaussian列向量g，按顺序包含x0、每拍w及五节点v的标准化坐标。到目标217需维度2+217(2+5×2)=2606。**程序只算系数矩阵，不抽取g。**

令X_k^-=M_k^- g，则

\[
M_k^+=S_kM_k^-,\quad
M_{k+1}^-=F_kM_k^++B_wQ^{1/2}E_{w,k}+B_vR^{1/2}E_{v,k}.
\tag{6}
\]

选择矩阵C_hat,j抽取x−epsilon_j，C_e抽取节点1的epsilon，得到

\[
\begin{aligned}
T_{h,a}&=C_{hat,j}(M_s^+-M_r^+),&\theta_{h,a}&=T_{h,a}g,\\
L_\eta&=\operatorname{col}_{k=211}^{216}
(H_1C_eM_k^++R_1^{1/2}E_{v_1,k}),&\eta^0&=L_\eta g,\\
L_0&=-C_eM_{217}^-,&e^0&=L_0g,\\
L_{z,h,a}&=L_\eta+O_hT_{h,a},&z&=L_{z,h,a}g.
\end{aligned}
\tag{7}
\]

两种独立坐标计算交叉核验：一套使用式(3)–(6)误差/对齐缓存；另一套直接使用物理x、原始hat、原始缓存、年龄A^age和原Yang更新计算系数。不输入完整仿真轨迹或未来sender差。

## 4. 任务要求的两个联合协方差

记V_theta=T T^T、C=Cov(theta,eta^0)=T L_eta^T、Sigma_eta=L_eta L_eta^T。均值在本冻结模型中全为0。精确等式为

\[
\boxed{\Sigma_{\theta z,h,a}=V_\theta O_h^T+C}
\tag{8}
\]

\[
\boxed{\Sigma_{zz,h,a}=\Sigma_\eta+O_hV_\theta O_h^T
+O_hC+C^TO_h^T.}
\tag{9}
\]

没有独立性近似。完整联合矩阵

\[
\operatorname{Cov}\begin{bmatrix}\theta\\z\end{bmatrix}
=\begin{bmatrix}V_\theta&\Sigma_{\theta z}\\
\Sigma_{z\theta}&\Sigma_{zz}\end{bmatrix}
\tag{10}
\]

由系数Gram矩阵直接半正定。健康误差和当前z还满足

\[
P_0=L_0L_0^T,\quad
C_{0\theta}=L_0T^T,\quad
C_{0z}=L_0L_\eta^T+C_{0\theta}O_h^T.
\tag{11}
\]

这些是实际缓存模型的误差矩，非算法报告协方差。受攻真实MSE为

\[
J_{a,h,a}=\operatorname{tr}(P_0+G_hV_\theta G_h^T
+C_{0\theta}G_h^T+G_hC_{0\theta}^T).
\tag{12}
\]

污染RMS sqrt(tr(G V_theta G^T))不等于sqrt(Ja−J0)，除非交叉项确实为0。

## 5. 正确的Soft Average

在固定h/a的联合Gaussian模型下，Sigma_zz正定时

\[
E[\theta\mid z,h,a]=\mu_\theta+
\Sigma_{\theta z}\Sigma_{zz}^{-1}(z-\mu_z),
\tag{13}
\]

\[
V_{\theta\mid z,h,a}=V_\theta-
\Sigma_{\theta z}\Sigma_{zz}^{-1}\Sigma_{z\theta}.
\tag{14}
\]

本次24个模型均可直接Cholesky，无ridge。若以后先验退化，应在其支持空间处理，不假造满秩。

名义a=64、p(h0)=.5、p(h)=.0625；正常模型z~N(0,Sigma_eta)、Delta=0。事件边际log似然必须含

\[
\log L_h=-\tfrac12[12\log(2\pi)+\log\det\Sigma_{zz,h}
+(z-\mu_{z,h})^T\Sigma_{zz,h}^{-1}(z-\mu_{z,h})].
\tag{15}
\]

用log-sum-exp更新w_h(z)∝p(h)L_h，标准软影响动作为

\[
\bar\Delta(z)=\sum_{h\ne h0}w_h(z)G_h E[\theta_h\mid z,h],
\quad u_S=\Pi_{\|u\|\le U}\bar\Delta(z)
\tag{16}
\]

并应用协议的正常校准门限。不能用exp(−r_h/2)冒充式(15)，不能将theta/eta独立时的公式套给Replay。年龄32/96测试时名义Soft仍用64，属于明确先验/源模型失配；若为每个真实年龄切换专用模型，就额外使用了攻击标签。

## 6. 必须纠正“Bayesian MMSE一定最优”的目标歧义

**DERIVED / STANDARD。** 无门限和幅度约束时，E[Delta|z]最小化E||Delta−u(z)||²，对应恢复健康反事实的污染残差。真实状态损失是E||e0+Delta−u(z)||²，所以其条件最优动作是

\[
u_x^{MMSE}(z)=E[e0+\Delta\mid z].
\tag{17}
\]

对固定h，E[e0|z,h]=C_0z Sigma_zz^{-1}(z−mu_z)；先验混合时同样按w_h求和，包括正常h0分量。式(17)严格指**修正动作仅为z的函数这一类中的最优动作**。hat x^a本身还依赖更多本地历史，因此hat x^a−E[e^a|z]一般不等于E[x217|完整本地历史]，不能把有限z的参照称为全信息物理状态MMSE。本协议只将式(17)作为理论参照，不新增第四个算法。

因此不能声称式(16)已是受攻真实MSE的无条件最优基线；更不能在胜过式(16)时声称战胜正确模型下的物理状态MMSE。附加U和正常非零概率限制后，普通无约束条件均值最优性也不能直接作为约束问题的全局最优证明。

已知h、不加限制的参照可精确验证

\[
J_{\text{soft-impact}}-J_{\text{state-MMSE}}
=\operatorname{tr}(C_{0z}\Sigma_{zz}^{-1}C_{z0})\ge0.
\tag{18}
\]

这由条件均值正交性得出，不是仿真比较，也不表示部署器已知h。若正确Bayes模型与全部合法历史信息均匹配，物理状态条件均值对相应先验平方损失最优；不预期集合方法无前提超过它。

## 7. Gaussian假设与集合覆盖的边界

固定h/a时上述Gaussian统计精确；随机但独立噪声的事件先验产生有限Gaussian混合，式(15)–(16)正确。对依赖载荷选择事件/来源的攻击，条件事件可能筛选底层噪声，Gaussian后验不再自动正确。

与此不同，集合检验使用的真h恒等式hat theta−theta=K_h eta^0及残差投影依然可以在固定日程成立。精确健康Sigma下，参数评分自由度2、残差评分自由度10；用同时覆盖处理事件选择，不把给定报警后的覆盖叫95%后验。这是频率覆盖与Bayes模型假设的区别，不能互相替代。

## 8. 数值证据、主实例和完整资产

Run：[g1r_replay_joint_20261114_r01](results/g1r_replay_joint_20261114_r01/summary.json)；[代码](code/replay_joint_statistics.py)。8事件×age32/64/96共24个精确模型。没有新轨迹、seed或E2原型。

主h=(0,200)、s=136、目标217：

\[
V_\theta=\begin{bmatrix}2320.691691&238.799442\\238.799442&25.733411\end{bmatrix},
\quad C_{0\theta}=\begin{bmatrix}.078227226&.043266012\\-.003223729&.002425264\end{bmatrix}.
\]

norm_F(C_theta,eta)=0.0498200，最大典型相关约0.066975；遗漏相关交叉项造成Sigma_zz的相对Frobenius变化约0.0009891。它是非零相关，但在该主模型上不足以宣称巨大性能收益。

主h的未约束、已知事件参照：软影响补偿真实MSE约0.291276；限于u(z)的真实状态损失最优修正参照约0.258490，两者差0.0327862，正好符合式(18)。这些都使用已知事件，仅作公式验证，不能计为部署算法结果或与有约束方案作不公平性能排名。结果字段中的true_state_MMSE_reference也仅表示这个受限信息修正参照，不是全历史最优状态估计器。

两种健康坐标的最大系数差1.4211e−14；与旧保存创新协方差最大差1.3878e−17；后验Schur/残差系数矩阵恒等式最大相对差4.5644e−16。全部24模型合法源已核验，联合矩阵半正定，未加ridge。

完整theta/z/e0加载、O、G、协方差和后验映射保存在[NPZ矩阵](results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz)，键case_edge_r_age明确事件/年龄；[逐模型CSV](results/g1r_replay_joint_20261114_r01/joint_cases.csv)给标量摘要。主实例Sigma_theta,z与Sigma_zz另输出CSV便于不使用Python的审阅者核对。来源哈希在Run冻结计划中；旧传播结果不覆盖。
