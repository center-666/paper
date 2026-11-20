# 独立数学审查：C记录下固定峰值的平方精度损伤阶

## 裁决

**定理A成立，限固定 \(b>0\)、\(k=0\)、\(m_0^-=0\) 和既定C记录。** 密度平衡反射给出保持整个C联合记录同律的合法随机攻击，损伤下界为 \(c\delta^2\)。C包含B，因此原B上界可继承；下面另给自含的 \(C_b\delta^2\) 上界。

定义
\[
K=\frac{P_0}{P_0+R}>0,\quad \lambda=AK\ne0,\quad
f(u)=\phi_{P_0+R}(u)(1-e^{-Zu^2/2}),\quad
p=\int f(u)\,du>0.
\]
固定任意 \(b>0\)。存在 \(\delta_b>0\) 和正常数 \(c,C_b\)，对 \(0<\delta\le\delta_b\) 有
\[
c\delta^2\le V_{R_C,\delta}^{(0)}(b,0)\le C_b\delta^2.
\tag{A1}
\]
常数独立于 \(\delta\)，可依赖系统和固定峰值。没有证明任意共同趋零 \(b,\delta\) 下的匹配双预算阶数。

## 1. 合法反射核：需修补量化边界

对非边界 \(u\)，令 \(c=Q_\delta(\lambda u)\)，定义
\[
\tau_\delta(u)=\frac{2c}{\lambda}-u.
\tag{A2}
\]
由于半开量化格的左边界反射会落到右边界，用户候选式在这些点不能直接声称码字相同。修补是：在可数集合
\[
\mathcal B_\delta=\{u:\lambda u=(2j+1)\delta,\ j\in\mathbb Z\}
\]
上定义 \(\tau_\delta(u)=u\)，即不动作。这不影响连续子概率积分，却保证所有路径的码字及幅值合同。

于是 \(\tau_\delta\) 为可测对合，在各开格上保持Lebesgue测度，
\[
Q_\delta(\lambda\tau_\delta(u))=Q_\delta(\lambda u),\qquad
|\tau_\delta(u)-u|\le \frac{2\delta}{|\lambda|}.
\tag{A3}
\]
开格内反射前后相对码中心的偏差互为相反数，边界修补后两值相等。

定义
\[
\alpha_\delta(u)=
\begin{cases}
\min\{1,f(\tau_\delta(u))/f(u)\},&f(u)>0,\\
0,&f(u)=0.
\end{cases}
\]
真实目标发送后，攻击方使用独立私有 \(\xi\sim{\rm Unif}[0,1]\)，以概率 \(\alpha_\delta(u)\) 把收到值改为 \(\tau_\delta(u)\)，否则保持 \(u\)。目标静默不读取量测且不动作；目标以后取零动作。私有接受随机数是原模型允许的信息，不能与传感器的私有触发随机数混淆。

当 \(2\delta/|\lambda|\le b\) 时，策略满足逐路径峰值。它只使用真实已发送量测、公开参数和独立私有随机数。

## 2. 发送子概率测度保持及完整C联合同律

给定发送真实量测 \(u\)，目标收到载荷 \(z\) 的核为
\[
\kappa_\delta(dz\mid u)
=\alpha_\delta(u)\delta_{\tau_\delta(u)}(dz)
+[1-\alpha_\delta(u)]\delta_u(dz).
\tag{A4}
\]
定义 \(w_\delta(u)=\min\{f(u),f(\tau_\delta(u))\}\)。除零测集外，
\[
f(u)\alpha_\delta(u)=w_\delta(u)=w_\delta(\tau_\delta(u)).
\]
对有界可测 \(h\)，反射换元给
\[
\begin{aligned}
\int f(u)\int h(z)\kappa_\delta(dz\mid u)\,du
&=\int w_\delta(u)h(\tau_\delta(u))\,du+
\int[f(u)-w_\delta(u)]h(u)\,du\\
&=\int f(z)h(z)\,dz.
\end{aligned}
\tag{A5}
\]
故发送收到载荷的次分布严格保持 \(f(z)\,dz\)。该证明是测度保持，不只是一两个矩不变。

设
\[
S_1=A^2\frac{P_0R}{P_0+R}+Q+R>0,\quad V_1=S_1+Z^{-1}.
\]
给定真实目标发送量测 \(u\) 与收到值 \(z\)，下一真实量测为 \(N(\lambda u,S_1)\)，下一实际触发中心为 \(c(z)=Q_\delta(\lambda z)\)。下一静默概率为
\[
s_1\exp[-(\lambda u-c(z))^2/(2V_1)],\qquad
s_1=(1+ZS_1)^{-1/2}.
\tag{A6}
\]
核(A4)的每一支路满足 \(z=u\) 或 \(z=\tau_\delta(u)\)，且 \(c(z)=c(u)\)。因此
\[
(\lambda u-c(z))^2=(\lambda z-c(z))^2
\quad\text{在整个核的支持上成立}.
\tag{A7}
\]
所以给定收到值 \(z\)，反射来源与拒绝来源对应的下一事件条件概率均等于健康的条件概率。结合(A5)，\((\gamma_0,\zeta_0,\gamma_1)\) 的联合律相同；目标静默支路完全不变。C中反馈码 \(c_0,c_1\) 及协方差标签 \(P_0^+,P_1^+\) 是这些变量与公开模型的确定函数，故
\[
\mathcal L_\pi(R_C)=\mathcal L_0(R_C).
\tag{A8}
\]
同时，B记录可在共享物理路径下逐路径相同，因为该反射不改变实际码中心；C记录一般只同律，并非逐路径相同。

## 3. 精确损伤与显式平方阶下界

对任意此类合法目标攻击，独立私有随机数不给出额外状态信息，故
\(\mathbb E[x_0\mid u,\gamma_0=1,\xi]=Ku\)。目标健康估计为 \(Ku\)，受攻为 \(Kz\)，所以
\[
J_{0,\delta}=K^2\mathbb E[\gamma_0(z-u)^2].
\]
对(A4)具体核，
\[
J_{0,\delta}
=K^2\int_{\mathbb R}\min\{f(u),f(\tau_\delta(u))\}
[\tau_\delta(u)-u]^2\,du.
\tag{A9}
\]
这一步不假定量测相关门控与健康估计误差独立；目标事件和标签先于动作，目标协方差项未变。

固定紧区间 \(I=[a,a+\ell]\subset(0,\infty)\)，其中 \(a,\ell>0\)，取
\[
m=\min_{u\in I}f(u)>0,\qquad h=\frac{2\delta}{|\lambda|}.
\]
仅计完整落在 \(I\) 内的u域量化格。它们等宽 \(h\)，反射仍留在自身格内，故(A9)中的密度最小值至少 \(m\)。若 \(h\le\ell/4\)，完整格总长 \(Nh\ge\ell-2h\ge\ell/2\)。每格中心记 \(u_j\)，则
\[
\int_{u_j-h/2}^{u_j+h/2}[\tau_\delta(u)-u]^2du
=4\int_{-h/2}^{h/2}t^2dt=\frac{h^3}{3}.
\]
因此
\[
J_{0,\delta}\ge K^2m\frac{Nh^3}{3}
\ge\frac{K^2m\ell h^2}{6}
=\boxed{\frac{2m\ell}{3A^2}\delta^2}.
\tag{A10}
\]
足够取 \(\delta\le\min\{b|\lambda|/2,\ell|\lambda|/8\}\)。这个下界无需证明接受概率趋于1，也不需要假定格内位置均匀；完整格积分直接给出常数。

## 4. 对全部允许策略的自含上界

固定 \(\delta_{\rm ref}>0\)。允许任意合法峰值 \(b\) 的目标动作 \(z-u\)，令
\[
R_*=|\lambda|b+\delta_{\rm ref},\qquad
q_*=\frac{1-e^{-R_*^2/(2V_1)}}{R_*^2}>0.
\]
目标事件本身未被攻击，所以 \(\mathbb E_\pi\gamma_0=\mathbb E_0\gamma_0=p\)。C记录可测统计量
\[
W=\frac{\gamma_0\mathbf1_{\{\gamma_1=0\}}}{s_1}
\]
在零TV时具有同一期望。健康的下一量化误差满足
\(|\lambda u-Q_\delta(\lambda u)|\le\delta\)，故
\[
p-\mathbb E_\pi W=p-\mathbb E_0W
\le \frac{p\delta^2}{2V_1}.
\tag{A11}
\]
受攻中 \(|\lambda u-Q_\delta(\lambda z)|\le|\lambda|b+\delta\le R_*\)。割线不等式与(A6)给
\[
q_*\mathbb E_\pi[\gamma_0(\lambda u-c(z))^2]
\le p-\mathbb E_\pi W.
\tag{A12}
\]
在带权 \(L^2(\gamma_0d\Pr_\pi)\) 中用三角不等式，
\[
\begin{aligned}
J_{0,\delta}
&=\frac1{A^2}\mathbb E_\pi[\gamma_0(\lambda u-\lambda z)^2]\\
&\le\boxed{\frac p{A^2}
\left(1+\frac1{\sqrt{2V_1q_*}}\right)^2\delta^2}.
\end{aligned}
\tag{A13}
\]
常数只依赖固定系统、固定 \(b\) 和 \(\delta_{\rm ref}\)，与实际 \(\delta\) 无关。它也可由原B类上界及C包含B得到；此处自含推导核对了条件化与量词。

在 \(k=0\) 下，全策略上确界是否允许时间1及以后动作不影响(A13)：它们在 \(\gamma_1\) 决定之后发生，不影响目标损伤或上述C字段。下界只需选目标后零动作子类。若把 \(\zeta_1,c_2\) 等额外字段加入记录，则不能沿用这一量词说明。

## 边界

- 结论为固定 \(b>0\) 的 \(\Theta(\delta^2)\)，没有得出同时变化预算的 \(\Theta(\min\{b^2,\delta^2\})\)。
- 构造并非最优策略，也未求渐近最优常数。
- 标量 \(AK\ne0\)、高斯条件后验、发送后权限、同一量化协议和指定有限记录均为显式条件。
- 端点自环及 \(f=0\) 时拒绝是零测但必要的全路径定义修补，不是删样本或放宽容差。
- 该证明使用标准的密度平衡/Metropolis接受思想；其数学工具本身不构成新颖性。需单独判断本协议与C/D记录分界是否为文献已覆盖结果。
