# 网格外幅值：小于半阶的分数矩与局部延迟保证

本文件独立补充 [05_fractional_moment_delay.md](05_fractional_moment_delay.md)，不改该文件的同幅值定理，不改核心算法、冻结协议或实验。仅解析推导，无随机样本。本节给网格足够细时的存在性保证，不声称目前三档候选已达到所需网格半径。

## 1. 为什么错幅值不能继续使用负半阶矩

记真实与候选当前核为
\[
K_a=K_{d_a,b_a},\qquad K_c=K_{d_c,b_c},
\quad
\ell_c=K_c(O)/K_0(O),
\]
定义沿用02/05：发送密度
\(f_{d,b}(u)=\phi_S(u-b-d)h(u-b-r)\)，静默质量
\(G(d,r)=s e^{-(d-r)^2/(2V)}\)。

若 \(b_c\ne0\) 且 \(b_a\ne b_c\)，候选发送密度在
\(u_*=r+b_c\) 有二阶零点，而
\[
f_c(u)\asymp (u-u_*)^2,\qquad
f_a(u_*)=\phi_S(r+b_c-b_a-d_a)h(b_c-b_a)>0,
\]
\[
f_0(u_*)=\phi_S(r+b_c)h(b_c)>0.
\]
所以真实分布下
\[
f_a(u)\left(\frac{f_0(u)}{f_c(u)}\right)^\lambda
\asymp |u-u_*|^{-2\lambda}.
\tag{1}
\]
因此 \(\lambda=1/2\) 时局部积分按 \(1/|u-u_*|\) 对数发散；\(\lambda>1/2\) 也发散。该障碍不是数值积分精度不足。05的同幅值半阶矩定理不能通过把真实幅值四舍五入到最近候选而继续使用。

这里排除了 \(b_c=0\) 的特殊取消情况；当前正幅值候选均满足 \(b_c\ne0\)。同幅值时真实和候选选择零点一致，05完成平方正是利用了这一点。

## 2. 小分数矩的可积性与连续性

固定
\[
0<\lambda<1/2\qquad\text{例如 }\lambda=1/4.
\]
真实分布下定义
\[
\begin{aligned}
M_\lambda(S,r,d_a,b_a,d_c,b_c)
&=\mathbb E_a[\ell_c^{-\lambda}\mid\mathcal I^-]\\
&=G(d_a,r)\left(\frac{G(0,r)}{G(d_c,r)}\right)^\lambda\\
&\quad+\int_{\mathbb R} f_{d_a,b_a}(u)
\left(\frac{f_{0,0}(u)}{f_{d_c,b_c}(u)}\right)^\lambda du.
\end{aligned}
\tag{2}
\]
考虑参数紧集：\(0<S_{\min}\le S\le S_{\max}<\infty\)、\(|r|\le\delta\)、真实/候选 \(d\) 有界、真实/候选 \(b\) 有界。静默概率在这种紧集上正且连续，所以静默项有限且连续。

对发送项，以候选零点为原点，令 \(z=u-r-b_c\)。唯一分母选择因子成为固定的 \(h(z)^\lambda\)，其局部倒数满足
\[
h(z)^{-\lambda}\le C|z|^{-2\lambda}\quad(0<|z|\le1).
\]
其余选择因子均不超过1，高斯项在紧集局部一致有界。由于 \(2\lambda<1\)，局部包络可积。

尾部也有统一高斯包络。令 \(m_a=b_a+d_a\)、\(m_c=b_c+d_c\)，则
\[
\phi_S(u-m_a)
\left(\frac{\phi_S(u)}{\phi_S(u-m_c)}\right)^\lambda
=C_\lambda(m_a,m_c,S)
\phi_S\bigl(u-(m_a-\lambda m_c)\bigr),
\tag{3}
\]
\[
C_\lambda=
\exp\left\{
\frac{\lambda[(1+\lambda)m_c^2-2m_am_c]}{2S}
\right\}.
\]
紧集上该常数及中心有界；远离候选零点时 \(h(z)^{-\lambda}\) 有界。因此存在统一可积包络，例如零点附近 \(C|z|^{-2\lambda}\)、尾部 \(C e^{-c z^2}\)。

对固定 \(z\ne0\)，变换后的被积函数对所有参数连续。支配收敛给出：

**引理1。** 对任意固定 \(\lambda\in(0,1/2)\)，式(2)在上述紧集上有限且连续，因此一致连续，并存在有限的统一上界 \(\overline M_\lambda\)。为方便后续可取
\[
\overline M_\lambda=\max\{1,\sup M_\lambda\}<\infty.
\tag{4}
\]
它可能远大于1；可积不等于立即具有检测收缩。若让 \(\lambda\uparrow1/2\)，不能把这一引理的常数当作仍然一致有界。

## 3. 匹配对角线上的严格收缩扩展到小邻域

另外限定真实幅值
\[
0<b_{\min}\le b_a\le b_{\max}<\infty.
\tag{5}
\]
在匹配对角线 \(d_c=d_a=d,\ b_c=b_a=b\) 上，
\[
M_\lambda(S,r,d,b,d,b)
=\int K_{d,b}^{\,1-\lambda}K_0^\lambda=:A_\lambda(S,r,d,b).
\tag{6}
\]
积分包含静默原子。Hölder不等式给 \(A_\lambda\le1\)，等号仅在两个概率核相同时成立。

对于 \(b\ne0\)，发送连续密度在 \(u=r\) 满足
\(f_0(r)=0\)、\(f_{d,b}(r)=\phi_S(r-b-d)h(-b)>0\)，故两个核不同。因此在固定紧 \(S,r,d,b\) 集上，连续性给
\[
\bar a_\lambda:=\max A_\lambda<1.
\tag{7}
\]
令 \(\bar r_\lambda=(1+\bar a_\lambda)/2<1\)。由引理1的一致连续性，存在某个正半径 \(\eta_\lambda>0\)，使
\[
|b_c-b_a|+|d_c-d_a|\le\eta_\lambda
\quad\Longrightarrow\quad
M_\lambda(S,r,d_a,b_a,d_c,b_c)\le\bar r_\lambda<1.
\tag{8}
\]
可缩小半径使候选仍在预先规定的扩大紧集中，例如 \(b_c\ge b_{\min}/2\)。这里距离两项均是当前标量状态/量测同一坐标下的幅值，未推广到量纲不同的多维变量。

**式(8)只证明半径存在。** 没有给出认证数值，不保证0.025或0.05的实际幅值间隔落在该邻域内。正的匹配信息量本身也不足以直接给出这两个具体网格偏差的功效。

## 4. 预测偏差失配的驱动递推与burn-in

真实攻击从 \(t_0\) 起持续取 \(b_a\)，候选轨道持续取 \(b_c\)，在同一实际事件历史和同一协方差/增益上运行。令
\(\Delta_t=d_{c,t}-d_{a,t}\)，则
\[
\Delta_{t+1}
=A(1-K_{\gamma_t})\Delta_t
-A\gamma_tK_1(b_c-b_a).
\tag{9}
\]
设 \(0\le A(1-K_\gamma)\le\rho<1\)，发送增益 \(K_1\le K_{\max}\)。于是
\[
|\Delta_{t_0+\ell}|
\le\rho^\ell|\Delta_{t_0}|
+C_b|b_c-b_a|(1-\rho^\ell),\qquad
C_b=\frac{A K_{\max}}{1-\rho}.
\tag{10}
\]
同幅值时驱动消失，退回05的几何衰减；错幅值时一般有非零残余误差，不能再宣称无限时域总KL失配有界。

取一个统一初始失配界 \(|\Delta_{t_0}|\le\Delta_{\max}\)。若候选幅值满足
\[
|b_c-b_a|\le\epsilon_b:=
\frac{\eta_\lambda}{2(1+C_b)},
\tag{11}
\]
并选预定 \(L\) 使 \(\rho^L\Delta_{\max}\le\eta_\lambda/2\)，则所有 \(\ell\ge L\) 有
\[
|b_c-b_a|+|\Delta_{t_0+\ell}|\le\eta_\lambda.
\]
因此从第 \(L\) 拍以后，式(8)逐历史保证条件负 \(\lambda\) 阶矩不大于 \(\bar r_\lambda<1\)。这里 \(L\) 是分析用burn-in，不需要检测器知道真实起点或在该时刻重置。

可给定开始前历史，以实际 \(|\Delta_{t_0}|\) 选择条件分析的 \(L\)；要得到对全部起点前史统一的界，则应使用 \(\Delta_{\max}\)。当前S1/U1可以用已有 \(P\) 和候选偏差包络给出这两个粗常数，但没有因此认证式(11)的实际网格半径。

## 5. 定理：足够近候选下的warm混合有限延迟

令
\[
L_m^c=\prod_{t=t_0}^{t_0+m-1}\ell_{c,t}.
\]
前 \(L\) 拍用式(4)的统一有限上界，之后用式(8)收缩。条件迭代给
\[
\boxed{
\mathbb E_a[(L_m^c)^{-\lambda}\mid\mathcal I_{t_0}^-]
\le
\overline M_\lambda^{\,\min(m,L)}
\bar r_\lambda^{(m-L)_+}.}
\tag{12}
\]
这个界允许攻击后早期候选失配造成证据不利增长；它没有把burn-in损失忽略。

当前J起点混合包含在 \(k_*=t_0+1\) 重启的组件，且共享候选倍率；候选权重为 \(\pi_j\)。设
\[
c_{k_*,j}=\log\frac1{\alpha w_{k_*}\pi_j}.
\tag{13}
\]
若该组件对数积达到 \(c_{k_*,j}\)，J必已报警。因此由Markov，
\[
\boxed{
\Pr_a(\tau_J>t_0+m\mid\mathcal I_{t_0}^-)
\le
\min\left\{1,\,
e^{\lambda c_{k_*,j}}\,
\overline M_\lambda^{\,\min(m,L)}
\bar r_\lambda^{(m-L)_+}\right\}.}
\tag{14}
\]
条件式可用于已经幸存到真实起点的前史；不能把起点前误报计为攻击检出。若攻击无限持续，式(14)给有限期望延迟。特别对 \(m\ge L\)，目标漏报 \(\beta\) 的一个充分观察数为
\[
m\ge L+
\frac{\lambda c_{k_*,j}
+L\log\overline M_\lambda+\log(1/\beta)}
{-\log\bar r_\lambda}.
\tag{15}
\]
向上取整即可。它是充分界，不是最优性结果。

本节的 \(\lambda\) 只用于证明当前LR混合检测器的尾部性质，不是把在线检测器改成负分数幂，也不改变其 \(1/\alpha\) 健康Ville阈值。固定选择 \(\lambda=1/4\) 已足以建立上述存在性；不需要借真实攻击幅值在线选 \(\lambda\)。

## 6. 当前三档网格可以声明到哪一步

- 健康误报保证仍对所有合法可预测候选成立，真实幅值是否落在网格内不影响02的e-factor归一化。
- 05的负半阶矩延迟保证要求严格同幅值，不能覆盖真实0.075与候选0.05/0.10、真实0.15与候选0.10/0.25的失配情况。
- 本节说明选择 \(\lambda<1/2\) 后，存在足够细的幅值网格与有限burn-in，可覆盖固定正幅值紧区间上的局部失配。
- **尚未认证 \(\epsilon_b\) 或 \(\bar r_\lambda\) 的数值。** 因而0.075、0.15仍只能依据冻结实验描述，不能写成本定理已保证的检测档位。
- 不从有限网格积分看见 \(M_\lambda<1\) 就宣称连续参数盒认证；还要控制移动奇点邻域、Gaussian尾及参数优化误差。越靠近 \(\lambda=1/2\)，奇点常数可能越差。
- 若要据本定理调整候选网格，必须另建并冻结新协议；不能在现有攻击测试结果上调细网格后仍声称沿用原冻结试验。

结论是：网格外理论并非被半阶矩发散完全堵住，但可证明范围是“固定正幅值紧区间、足够近候选、足够burn-in”的存在性结果。它没有证明目前三个候选对所有中间幅值都有实用有限时间功效，也没有绕过工程实验和同信息强基线。
