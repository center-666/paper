# 量化反馈 C/D 记录分界：两项定理的合并审查

日期：2026-11-20。基准提交：ca79c623874e77d150dc7fa58f77e83c43c320a0。

**数学裁决：两项候选定理均 PASS，严格限于各自声明的记录和攻击时域。文献新颖性：OPEN。** 本报告合并两份独立数学核查与一次定向全文审查；不是期刊同行评审或形式化证明认证。没有修改正式论文、没有运行实验。

## 1. 统一协议、策略类与记录

采用原稿标量模型：
\[
x_0\sim N(0,P_0),\quad m_0^-=0,\quad y_0=x_0+v_0,\quad
x_1=Ax_0+w_0,\quad y_1=x_1+v_1,
\]
其中 \(P_0,R,Z>0\)、\(Q\ge0\)、\(A\ne0\)，\(v_0,v_1\sim N(0,R)\)、\(w_0\sim N(0,Q)\)、\(U_0,U_1\sim{\rm Unif}[0,1]\)，初态、物理噪声、触发随机数及攻击私有种子相互独立。物理过程不受接收估计控制，排除丢包及时延。

令
\[
K=\frac{P_0}{P_0+R},\quad P_s=\frac{P_0R}{P_0+R},\quad
\lambda=AK\ne0,\quad S_0=P_0+R,\quad S_1=A^2P_s+Q+R.
\]
反馈量化器和静默规则为
\[
c_t=Q_\delta(m_t^-),\quad
Q_\delta(m)=2\delta\left\lfloor\frac{m+\delta}{2\delta}\right\rfloor,\quad
\gamma_t=0\iff U_t\le e^{-Z(y_t-c_t)^2/2}.
\]
量化格半开、无限且无饱和。发送更新为原Kalman形式，静默更新仍使用实际码中心：
\[
m_t^+=
\begin{cases}
m_t^-+K_1(P_t^-)(\tilde y_t-m_t^-),&\gamma_t=1,\\
m_t^-+K_0(P_t^-)(c_t-m_t^-),&\gamma_t=0,
\end{cases}
\quad m_{t+1}^-=Am_t^+.
\]
\(P_t^+=F_{\gamma_t}(P_t^-)\)、\(P_{t+1}^-=A^2P_t^++Q\)，
\(K_i(P)=P/(P+R_i)\)、\(F_i(P)=P-P^2/(P+R_i)\)，\(R_1=R,\ R_0=R+Z^{-1}\)。

令 \(\Pi_{\rm ss}(b)\) 为全部单拍策略：仅在目标0拍真实发送后，可读取真实已发 \(u=y_0\)，用公开模型和独立私有种子选择收到载荷 \(z=u+a_0\)，逐路径 \(|a_0|\le b\)；静默时动作零，时间1及以后无动作。允许任意量测相关随机策略，不限线性或反射形式。它不能读取隐藏状态、传感器触发随机数、未发送量测或未来噪声。

记录按层定义：
\[
\begin{aligned}
R_B&=(\gamma_0,\gamma_1,c_0,c_1,P_0^+),\\
R_C&=(R_B,\zeta_0,P_1^+),\\
R_D&=(R_C,\zeta_1),
\end{aligned}
\tag{1}
\]
其中发送时 \(\zeta_t=\tilde y_t\)、静默时 \(\zeta_t=\bot\)。协方差为按事件递推的名义标签，不是额外真实状态信息。C不包括 \(\zeta_1,m_1^+,m_2^-,c_2\)。D中的下一连续载荷未经修改，是单拍策略条件的结果，不擅自假设所有多拍攻击都满足该条件。

统一定义
\[
J_{0,\delta}(\pi)=\mathbb E_\pi(x_0-m_0^+)^2-\mathbb E_0(x_0-m_0^+)^2,\qquad
V_{R,\delta}^{\rm ss}(b,0)=
\sup_{\pi\in\Pi_{\rm ss}(b),\,\mathcal L_\pi(R)=\mathcal L_0(R)}
J_{0,\delta}(\pi).
\tag{2}
\]
两边比较同一量化协议。原允许所有时间载荷修改的策略类记为 \(\Pi_{\rm all}(b)\)，原最坏值记为 \(V_{R,\delta}^{(0)}\)；第4节说明 C 的两类最坏值相同。本文不为D作这样的扩类。

## 2. 通用条件后验与损伤恒等式

目标中心 \(c_0=0\)，真实发送子概率密度为
\[
f(u)=\phi_{S_0}(u)\left(1-e^{-Zu^2/2}\right),\qquad
p=\int f(u)\,du=1-(1+ZS_0)^{-1/2}>0.
\tag{3}
\]
\(\phi_S\) 表示方差 \(S\) 的中心高斯密度。给定真实发送量测 \(u\)，事件似然只是 \(u\) 的函数，且攻击随机种子独立于物理残差，因此
\[
x_0\mid(u,\gamma_0=1,z)\sim N(Ku,P_s),\quad
y_1\mid(u,\gamma_0=1,z)\sim N(\lambda u,S_1).
\tag{4}
\]
式(4)描述真实物理量测，与时间1的载荷修改无关；原模型中的攻击不能直接改变物理 \(y_1\)。第5节将接收载荷 \(\zeta_1\) 等同于 \(y_1\) 时，才使用时间1不攻击的条件。得到目标收到载荷 \(z\) 的随机核可能是离散、连续或混合，(4)不要求其有密度。

目标健康估计为 \(Ku\)，受攻估计为 \(Kz\)，目标静默支路未变。条件正交性给出对全部合法目标策略成立的精确关系
\[
J_{0,\delta}(\pi)=K^2\mathbb E_\pi[
\mathbf1_{\{\gamma_0=1\}}(z-u)^2]\ge0.
\tag{5}
\]
这里未假设动作与量测或门控与残差独立；独立性仅用于给定 \(u\) 后攻击随机性不泄漏隐藏残差。目标事件和协方差标签分布不变，目标协方差项已消去。

## 3. 定理 A：C 下固定峰值的精度平方阶

**定理 A。** 固定模型及任意 \(b>0\)。存在 \(\delta_b,c,C_b>0\)，使全部 \(0<\delta\le\delta_b\) 有
\[
\boxed{c\delta^2\le V_{R_C,\delta}^{\rm ss}(b,0)
=V_{R_C,\delta}^{(0)}(b,0)\le C_b\delta^2.}
\tag{6}
\]
常数独立于实际 \(\delta\)，可依赖模型、固定 \(b\) 及预先取定的精度上限。没有声称 \(b,\delta\) 同时趋零时的匹配双预算阶数。

### 3.1 保持发送密度的合法格内反射

非边界点定义
\[
c_\delta(u)=Q_\delta(\lambda u),\qquad
T_\delta(u)=2c_\delta(u)/\lambda-u.
\tag{7}
\]
在可数边界集 \(\{\lambda u=(2j+1)\delta:j\in\mathbb Z\}\) 上改为 \(T_\delta(u)=u\)。这修补半开格左端点反射到右端点的问题。该集合的发送子测度为零，修补不是筛选样本；它使峰值及码字合同在所有路径上成立：
\[
T_\delta(T_\delta(u))=u,\quad
Q_\delta(\lambda T_\delta(u))=Q_\delta(\lambda u),\quad
|T_\delta(u)-u|\le 2\delta/|\lambda|.
\tag{8}
\]
结论同时覆盖 \(\lambda<0\)：在 \(u\) 轴的格仍等宽，只是端点开闭方向反转；边界已统一自环。

真实发送后，以攻击私有独立均匀随机数作接受：
\[
\alpha_\delta(u)=
\begin{cases}
\min\{1,f(T_\delta(u))/f(u)\},& f(u)>0,\\
0,&f(u)=0.
\end{cases}
\]
接受时令 \(z=T_\delta(u)\)，否则令 \(z=u\)，目标后不动作。只要 \(\delta\le b|\lambda|/2\)，便满足逐路径幅值限制。这个种子不是传感器触发随机数。

用 \(\delta_x^{\rm Dirac}\) 区别Dirac测度与精度参数，核为
\[
\kappa_\delta(dz\mid u)=
\alpha_\delta(u)\delta_{T_\delta(u)}^{\rm Dirac}(dz)
+[1-\alpha_\delta(u)]\delta_u^{\rm Dirac}(dz).
\tag{9}
\]
令 \(w_\delta(u)=\min\{f(u),f(T_\delta(u))\}\)。因 \(T_\delta\) 在每个格内保持Lebesgue测度且为对合，\(w_\delta(T_\delta(u))=w_\delta(u)\)。对任意有界可测 \(h\)，
\[
\begin{aligned}
\int f(u)\int h(z)\kappa_\delta(dz\mid u)\,du
&=\int w_\delta(u)h(T_\delta(u))\,du
 +\int(f(u)-w_\delta(u))h(u)\,du\\
&=\int f(z)h(z)\,dz.
\end{aligned}
\tag{10}
\]
这就是标准详细平衡接受规则在目标发送子测度上的应用，不是新采样算法。

### 3.2 联合下一事件核必须同时保持

收到 \(z\) 后，接收预测为 \(\lambda z\)，下一中心为 \(c_\delta(z)\)。由(4)，
\[
\Pr_\pi(\gamma_1=0\mid u,z,\gamma_0=1)
=s_1\exp[-(\lambda u-c_\delta(z))^2/(2V_1)],
\quad s_1=(1+ZS_1)^{-1/2},\quad V_1=S_1+Z^{-1}.
\tag{11}
\]
核(9)的每一支路都有 \(z=u\) 或 \(z=T_\delta(u)\)，且
\[
(\lambda u-c_\delta(z))^2=(\lambda z-c_\delta(z))^2.
\tag{12}
\]
因此下一事件条件核在所有可能来源 \(u\) 上只依赖收到值 \(z\)，且等于健康给定 \(z\) 的核。结合(10)，发送分支的 \((z,\gamma_1)\) 联合子测度严格相同；目标静默分支未改。全部C字段由这些共同变量及模型确定，所以 C 联合记录同律。

仅发送密度保持不足以证明该结论；(12)是额外所需的触发核保持性质。B字段可在共享物理路径下相同；C一般只同律，不逐路径相同。

### 3.3 显式平方阶下界

由(5)，构造的精确损伤为
\[
J_{0,\delta}=K^2\int_\mathbb R w_\delta(u)
[T_\delta(u)-u]^2\,du.
\tag{13}
\]
固定 \(I=[a,a+\ell]\subset(0,\infty)\)，\(a,\ell>0\)，取
\[
m=\min_{u\in I}f(u)>0,\qquad h=2\delta/|\lambda|.
\]
考虑全部完整包含在 \(I\) 的 \(u\)-格，共 \(N\) 个。若 \(h\le\ell/4\)，边缘至多舍去两个不完整格，有 \(Nh\ge\ell-2h\ge\ell/2\)。这些格上的 \(u,T_\delta(u)\) 都在 \(I\)，故 \(w_\delta(u)\ge m\)。每格中心 \(u_j\) 满足
\[
\int_{u_j-h/2}^{u_j+h/2}[T_\delta(u)-u]^2du
=4\int_{-h/2}^{h/2}t^2dt=h^3/3.
\]
于是
\[
\boxed{J_{0,\delta}\ge K^2mNh^3/3
\ge \frac{2m\ell}{3A^2}\delta^2.}
\tag{14}
\]
此处只对下界忽略其他格的非负贡献，策略仍定义于全部格；没有删除观测。也不要求格内相位均匀或先证明接受率趋于1。取
\(\delta_b\le\min\{b|\lambda|/2,\ell|\lambda|/8,\delta_{\rm ref}\}\)
即同时满足合法性和下界条件。

## 4. C 的全策略上界及量词

任意C-零TV合法策略均使
\[
W=\mathbf1_{\{\gamma_0=1,\gamma_1=0\}}/s_1
\]
的期望与健康相同。健康时量化误差不超过 \(\delta\)，由 \(1-e^{-x}\le x\) 得
\[
p-\mathbb E_0W\le p\delta^2/(2V_1).
\tag{15}
\]
对受攻发送支路，记 \(d=\lambda u-Q_\delta(\lambda z)\)。固定 \(\delta\le\delta_{\rm ref}\) 时，
\[
|d|\le R_*:=|\lambda|b+\delta_{\rm ref},\qquad
q_*=\frac{1-e^{-R_*^2/(2V_1)}}{R_*^2}>0.
\]
割线不等式给 \(1-e^{-d^2/(2V_1)}\ge q_*d^2\)。利用(11)、同律和(15)：
\[
q_*\mathbb E_\pi[\mathbf1_{\{\gamma_0=1\}}d^2]
\le p-\mathbb E_\pi W
=p-\mathbb E_0W\le p\delta^2/(2V_1).
\tag{16}
\]
另外 \(\lambda(u-z)=d-(\lambda z-Q_\delta(\lambda z))\)。在发送分支加权 \(L^2\) 中用三角不等式，结合(5)得
\[
\boxed{J_{0,\delta}\le C_b\delta^2,\quad
C_b=\frac p{A^2}\left(1+\frac1{\sqrt{2V_1q_*}}\right)^2.}
\tag{17}
\]
它也可继承旧B记录上界；这里自含推导再次核对了量词和选择性观察。

在 \(k=0\) 下，时间1及以后动作不影响目标损伤、\(\gamma_1\) 或 \(P_1^+\)，C又不记录下一载荷或后续预测。因此将任意 \(\Pi_{\rm all}(b)\) 策略截断到目标拍，不改变其C记录分布和目标损伤，故(6)中两类最坏值相等。D包含下一载荷，不能据此将D结果扩展到多拍攻击。

## 5. 定理 B：D 对全部单拍攻击的零TV唯一性

**定理 B。** 对每个 \(b,\delta>0\) 及任意 \(\pi\in\Pi_{\rm ss}(b)\)，
\[
\boxed{\mathcal L_\pi(R_D)=\mathcal L_0(R_D)
\ \Longrightarrow\ a_0=0\ {\rm a.s.}
\ \Longrightarrow\ J_{0,\delta}(\pi)=0.}
\tag{18}
\]
特别地 \(V_{R_D,\delta}^{\rm ss}(b,0)=0\)。反方向也成立：单拍策略的实际动作若几乎处处为零，则全部截至时间1的记录与健康相同。这里只是该策略类内的唯一性，不是所有攻击时域的必要充分条件。

### 5.1 从联合记录取得正则条件测度

任意合法随机目标动作都由发送分支上的Markov核 \(\kappa(dz\mid u)\) 表示。令有限测度
\[
M(du,dz)=f(u)\,du\,\kappa(dz\mid u),\qquad
\eta(dz)=M(\mathbb R,dz).
\]
D同律投影到目标发送载荷，先得
\[
\eta(dz)=f(z)\,dz.
\tag{19}
\]
在标准Borel空间上，将质量 \(p\) 归一化并用正则条件分布，可写
\[
M(du,dz)=\nu_z(du)\eta(dz).
\tag{20}
\]
\(\nu_z\) 只需对 \(\eta\)-几乎处处的 \(z\) 定义；它不需要密度，可能含原子。攻击独立种子在给定真实 \(u\) 后不泄漏隐藏高斯残差，因此(4)也适用于此核。

### 5.2 消去选择性发送因子

给定收到值 \(z\)，下一实际中心 \(c(z)=Q_\delta(\lambda z)\) 已知。记
\[
q_1(y;z)=1-e^{-Z(y-c(z))^2/2}.
\]
时间1无动作，发送时接收的连续值就是 \(y_1\)。因此 \(\gamma_0=\gamma_1=1\) 上的联合子测度分别为
\[
\begin{aligned}
M_\pi^{11}(dz,dy)
&=\eta(dz)q_1(y;z)
\left[\int\phi_{S_1}(y-\lambda u)\nu_z(du)\right]dy,\\
M_0^{11}(dz,dy)
&=f(z)dz\,q_1(y;z)\phi_{S_1}(y-\lambda z)dy.
\end{aligned}
\tag{21}
\]
D同律使两者相同。由(19)、Radon–Nikodym唯一性及Fubini，存在一个 \(\eta\)-满测集，集内每个 \(z\) 都有两个 \(y\)-密度Lebesgue几乎处处相同。对每个这样的 \(z\)，\(q_1(y;z)\) 除唯一点 \(y=c(z)\) 外严格正，故
\[
\int\phi_{S_1}(y-\lambda u)\nu_z(du)
=\phi_{S_1}(y-\lambda z)\qquad\text{Lebesgue-a.e. }y.
\tag{22}
\]
没有在单点零分母上相除，也没有把两个边缘相同当成联合相同。该满测集是在取Fourier变换前固定的；不对不可数多个频率作逐个零测集交集。

### 5.3 高斯卷积可辨识

式(22)两侧都是概率密度。取特征函数，Tonelli/Fubini允许交换概率积分：
\[
e^{-S_1t^2/2}\int e^{it\lambda u}\nu_z(du)
=e^{-S_1t^2/2}e^{it\lambda z},\qquad t\in\mathbb R.
\]
高斯特征函数处处非零，消去后由特征函数唯一性知
\[
(\lambda\cdot)_\#\nu_z=\delta_{\lambda z}^{\rm Dirac}.
\]
因 \(\lambda\ne0\)，\(\nu_z=\delta_z^{\rm Dirac}\)。对(20)积分回去，得目标发送分支 \(z=u\) 几乎处处；静默分支按权限本来就有 \(a_0=0\)。于是(18)成立。

## 6. 成对结论、限制与决定

在同一单拍权限内，有
\[
V_{R_C,\delta}^{\rm ss}(b,0)=\Theta(\delta^2)
\quad(b>0\text{固定},\delta\to0),\qquad
V_{R_D,\delta}^{\rm ss}(b,0)=0.
\tag{23}
\]
当前收到的连续载荷还不足以恢复零TV安全；当前与下一未修改连续载荷的联合信息则足以唯一识别该类单拍动作。C的平方阶不是仅在一个零附近小格上的特殊见证，而是许多完整格的损伤累积。

必须保留：

- D要求下一拍不攻击，且确实保留其发送时的连续载荷；不能在结论中悄然换回任意多拍权限。
- 两项结论均为严格总体零TV；没有非零TV稳定常数、检验样本复杂度或在线检测保证。几乎处处正的发送权重足够辨识，并不意味着逆问题数值条件良好。
- 目标为0拍、初始预测为零；没有把健康目标前史条件化推广到一般 \(k\) 或随机隐藏历史。
- \(AK\ne0\)、外生物理过程和合法独立攻击种子是D可辨识的关键条件；状态矩阵为零或攻击读取隐藏残差时该证明失效。
- C的下界阈值 \(\delta_b\) 依赖固定 \(b\)，不能由它宣称任意共同趋零预算的匹配阶数。
- 已知 \(m_1^-=\lambda z\) 可从C恢复；单独加它不增加信息。D的重要性在跨时联合关系，不在单独一拍连续数据更精细。

标准详细平衡与高斯去卷积本身不构成新原理，D的辨识思路也不专属于均匀量化。潜在增量是完整协议、权限、记录和损伤目标下的成对分离。定向全文比较未发现已核近邻直接给出这对同条件结果；全球新颖性仍OPEN。可将其作为新的候选理论资产供用户决策，但本轮不据此重构现稿、不设计防御、不启动更多理论或实验。

## 核查材料

- [C独立数学审查](agent_a_audit.md)
- [D独立数学审查](agent_b_audit.md)
- [合并稿的独立回读与修正清单](agent_b_pair_readback.md)
- [近邻与JAS官方全文审查](03_novelty_and_jas_fulltext_audit.md)
- [官方全文来源清单](jas_fulltext_source.json)
- [上一轮局部反射证明](../paper1_quantized_reflection_audit_20261120/01_local_reflection_joint_record_proof.md)
