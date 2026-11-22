# 幅值可辨识、起点信息有限与当前污染的功能收缩

日期：2026-11-22。基准提交 e1c55269。本文件仅进行解析推导，不生成随机样本，不修改阶段三代码或正式论文。置信失效概率记作 \(\varepsilon\)，量化半步长仍记作 \(\delta\)，两者不混用。

**适用记录：可信事件、连续发送载荷及精确实际量化中心。** 接收端没有单独保存原始相位字段也可以，只要精确中心可恢复。若只保留整数码字且历史中心未保存，条件先验一般不再保持当前单高斯闭合，以下精确序贯似然必须重建，不能直接沿用。

## 1. 同一已观测历史上的条件核

当前实际 monitor 预测为 \(m_t^-\)，协方差标签为 \(P_t^-\)，精确中心残差为 \(r_t=c_t-m_t^-\)。在候选 \(\vartheta=(k,b)\) 下，当前发送后注入幅值为
\[
a_t(\vartheta)=b\,\mathbf1_{\{t\ge k\}},
\]
而实际修改仍只在 \(\gamma_t=1\) 时发生。记候选真实条件预测均值相对 monitor 的偏差为 \(d_t(\vartheta)\)，则
\[
S_t=P_t^-+R,\quad V_t=S_t+Z^{-1},\quad
h(v)=1-e^{-Zv^2/2},
\]
\[
G(d;r,S)=\frac{e^{-(d-r)^2/(2V)}}{\sqrt{1+ZS}},\qquad
f_{d,a}(u;r,S)=\phi_S(u-a-d)\,h(u-a-r).
\tag{1}
\]
静默对应质量 \(G\)，发送对应连续次密度 \(f\)，并且 \(G+\int f=1\)。这是同一实际接收历史下的核比较：\(m,P,r\) 相同，候选的 \(d,a\) 不同；不是比较反馈中心不同的两条仿真反事实轨道。

精确中心在当前相位揭示前的条件分布在两候选下相同，因此中心自身的条件密度因子抵消。条件于中心的下述界可再对中心取期望。有限历史的共同支配测度为逐拍“静默原子＋发送 Lebesgue 测度”与可信中心条件测度的乘积。

候选污染系数满足
\[
H_{k,t}^{+}=(1-K_{\gamma_t})H_{k,t}^{-}
+\gamma_tK_1\mathbf1_{\{t\ge k\}},\qquad
H_{k,t+1}^{-}=AH_{k,t}^{+},\qquad H_{k,0}^{-}=0.
\tag{2}
\]
于是后验污染及先验偏差分别为
\[
\theta_t(k,b)=bH_{k,t}^{+}\ge0,\qquad d_t(k,b)=-bH_{k,t}^{-}.
\tag{3}
\]
这些系数由实际可信事件历史和已知参数决定，不需要真实状态或原始未修改载荷副本。

以下使用从既有 Riccati 不变区间得到的确定包络
\[
0<S_-\le S_t\le S_+,\quad |r_t|\le\delta,\quad
0\le\theta_t(k,b)\le B,\quad |d_t(k,b)|\le D:=AB,
\tag{4}
\]
及
\[
0\le A(1-K_{\gamma_t})\le\rho<1.
\tag{5}
\]
S1/U1 均满足这些条件。可取发送 Riccati 正不动点 \(p_-\)、\(p_+=\max\{P_0,p_*(R+Z^{-1})\}\)，
\[
k_-=\frac{p_-}{p_-+R},\quad k_+=\frac{p_+}{p_++R},\quad
\rho=\frac{A(R+Z^{-1})}{p_-+R+Z^{-1}},
\]
\[
c_B=\max_{K\in[k_-,k_+]}\frac K{1-A(1-K)},\qquad
B=c_Bb_{\max},\quad S_-=p_-+R,\quad S_+=p_++R.
\tag{6}
\]
式(6)要求 \(P_0\ge p_-\)、所有分母为正；本轮参数满足。该 \(B\) 是整个允许幅值范围的后验污染界。

## 2. 不同当前幅值不能由历史均值污染完全遮蔽

考虑共同 \(S,r\) 下两个核 \(K_{d_1,a_1}\)、\(K_{d_2,a_2}\)。若 \(a_1\ne a_2\)，在 \(u=r+a_1\) 处，
\[
f_{d_1,a_1}(r+a_1)=0,\qquad
f_{d_2,a_2}(r+a_1)
=\phi_S(r+a_1-a_2-d_2)h(a_1-a_2)>0.
\tag{7}
\]
两个密度连续，故不可能 Lebesgue 几乎处处相同。这里不是把单个零概率点当作有正概率的信息事件，而是用连续性证明两个概率核本身不同。

定义 Hellinger 亲和度
\[
\mathcal A(K_1,K_2)=\sqrt{G_1G_2}+\int_{\mathbb R}\sqrt{f_1f_2}\,du.
\]
归一化和 Cauchy–Schwarz 给 \(\mathcal A\le1\)，等号当且仅当两个核相同。所以 \(a_1\ne a_2\) 时 \(\mathcal A<1\)，不要求 \(d_1=d_2\)。

在紧参数盒
\[
S\in[S_-,S_+],\quad |r|\le\delta,\quad
d_i\in[-D,0],\quad a_i\in[0,b_{\max}],
\]
再限制 \(|a_1-a_2|\ge\eta>0\)。统一高斯尾包络和 \(0\le h\le1\) 保证亲和度对全部参数连续；约束集合紧，故
\[
\boxed{
a_\eta:=\max_{|a_1-a_2|\ge\eta}\mathcal A(K_{d_1,a_1},K_{d_2,a_2})<1.
}
\tag{8}
\]
这是解析存在性，不是已计算并认证的数值收缩率。离散载荷、中心舍入或只读索引后的投影核不保留相同零点结构，必须重证。

## 3. 同幅值不同固定起点：无限历史仍只有有限 KL

固定 \(k_1<k_2\) 和同一 \(b>0\)，记真实候选为 \(\vartheta_1=(k_1,b)\)，另一候选为 \(\vartheta_2=(k_2,b)\)。沿共同观测历史，令
\[
\Delta_t=d_t(\vartheta_1)-d_t(\vartheta_2).
\]
从 \(t=k_2\) 起两边当前注入相同，式(2)给
\[
\Delta_{t+1}=A(1-K_{\gamma_t})\Delta_t,\qquad
|\Delta_{k_2+n}|\le\rho^n|\Delta_{k_2}|\le \rho^n AB.
\tag{9}
\]
给定同一 \(r,S\)，两个潜在真实创新是 \(N(d_1,S)\) 与 \(N(d_2,S)\)，经过同一个“真实创新决定发送、发送后加同一个 \(b\)”随机通道。KL 数据处理给
\[
\operatorname{KL}(K_{d_1,b}\Vert K_{d_2,b})
\le\frac{(d_1-d_2)^2}{2S}.
\]
因此
\[
\sum_{t=k_2}^{\infty}
\operatorname{KL}(K_{\vartheta_1,t}\Vert K_{\vartheta_2,t})
\le\frac{\Delta_{k_2}^2}{2S_-(1-\rho^2)}
\le\frac{A^2B^2}{2S_-(1-\rho^2)}.
\tag{10}
\]

### 有限起点间隔的 KL 也需证明有限

“只有有限拍”本身不能排除某一拍的无穷 KL。此处密度零点只产生可积的对数奇点，可给一个显式统一上界。令 \(M=b_{\max}+D\)、\(V_-=S_-+Z^{-1}\)。高斯对数密度比为关于 \(u\) 的仿射函数，且 \(f_1(u)\le\phi_{S}(u-a_1-d_1)\)，因此其绝对积分不超过
\[
U_{\rm Gauss}
=\frac{2M(2M+\sqrt{S_+})}{S_-}.
\]
触发项利用
\[
\log h(u-a_1-r)-\log h(u-a_2-r)\le-\log h(u-a_2-r)
\]
和
\[
\int_{\mathbb R}-\log(1-e^{-Zv^2/2})\,dv
=\sqrt{\frac{2\pi}{Z}}\,\zeta(3/2)<\infty
\tag{11}
\]
可界为 \(\zeta(3/2)/\sqrt{ZS_-}\)。式(11)由
\(-\log(1-x)=\sum_{j\ge1}x^j/j\) 和 Tonelli 逐项高斯积分得到。静默对数比绝对值不超过 \((D+\delta)^2/(2V_-)\)。于是共同参数盒内所有核对满足
\[
\operatorname{KL}(K_1\Vert K_2)\le U<\infty,
\quad
U=\frac{(D+\delta)^2}{2V_-}
+\frac{2M(2M+\sqrt{S_+})}{S_-}
+\frac{\zeta(3/2)}{\sqrt{ZS_-}}.
\tag{12}
\]
这是刻意宽松的上界，仅用于建立有限性，不作为检测功效预测。

记完整已观测历史为 \(O_{0:T}\)，包括可信精确中心。攻击前 \(t<k_1\) 的两核完全相同。KL 链式法则与式(10)/(12)给所有 \(T\)
\[
\boxed{
\operatorname{KL}(P_{\vartheta_1}^{0:T}\Vert P_{\vartheta_2}^{0:T})
\le (k_2-k_1)U+\frac{A^2B^2}{2S_-(1-\rho^2)}
=:C_{k_1,k_2,b}<\infty.
}
\tag{13}
\]
无限序列的相对熵是有限前缀相对熵的上确界，故仍不超过 \(C\)。对任意基于截至 \(T\) 记录的二元判别 \(\psi_T\)，Bretagnolle–Huber 不等式给
\[
\boxed{
P_{\vartheta_1}(\psi_T=2)+P_{\vartheta_2}(\psi_T=1)
\ge\tfrac12 e^{-C_{k_1,k_2,b}}>0.
}
\tag{14}
\]
所以不存在一个方法，对这两个固定起点都让错误概率随单条轨迹的观察长度趋于零。由任何假设下都一致恢复起点的估计器可构造相应一致二元检验，故这种起点估计器也不存在。结论不排除某个有限起点对已经高度可分；上界 \(C\) 很大时式(14)可能极弱。独立重置并重复观察同一个起点问题也不在该“一条越来越长记录”结论内。

## 4. 精确混合参考与有限幅值字典

固定有限正幅值字典
\[
\mathcal B=\{b_1,\ldots,b_J\}\subset(0,b_{\max}],
\qquad \vartheta^\star=(k^\star,b^\star),\quad b^\star\in\mathcal B.
\]
参数族包含全部 \(k\in\mathbb N_0\)、\(b\in\mathcal B\) 及一个健康模型。让参考历史密度为
\[
q_t=\pi_{\rm h}p_{0,t}
+(1-\pi_{\rm h})\sum_{k=0}^\infty w_k
\sum_{j=1}^J v_jp_{k,b_j,t},
\tag{15}
\]
其中 \(0\le\pi_{\rm h}<1\)、\(w_k>0\)、\(\sum_kw_k=1\)、\(v_j>0\)、\(\sum_jv_j=1\)。所有 \(p_{k,b_j,t}\) 使用自己的精确物理起点及偏差递推。真实原子权重
\[
\pi_\star=(1-\pi_{\rm h})w_{k^\star}v_{j^\star}>0
\]
给逐路径不等式 \(q_t\ge\pi_\star p_{\star,t}\)。

按标准似然反演定义
\[
C_t=\{\vartheta:p_{\vartheta,t}>\varepsilon q_t\}.
\tag{16}
\]
固定真实参数的全时域覆盖至少 \(1-\varepsilon\)。该覆盖可使用更一般的正规化参考 \(Q\)，但本节收缩依赖式(15)的精确真实原子质量，不能直接替换为阶段三 warm/P1 的 \(Q\) 后沿用同一收缩率。

**有限字典范围不可偷换。** 本节 \(C_t\) 中允许的幅值也只取 \(\mathcal B\)（外加健康）。若只把参考 \(Q\) 的幅值限制在字典，而反演集合仍包含连续区间 \([0,b_{\max}]\)，本节的有限候选并合计数并不成立。连续族覆盖仍有效，连续族收缩需另行熵/区间似然分析。

若 \(C_t\ne\varnothing\)，定义
\[
L_t=\inf_{\vartheta\in C_t}\theta_t(\vartheta);
\]
若集合为空或无法认证则取 \(L_t=0\)。可选上界 \(U_t=\sup_{C_t}\theta_t\) 同理。将所有 \(k>t\) 和健康候选合并为一个当前“尚无作用”的等价类：它们截至 \(t\) 的似然均为 \(p_{0,t}\)、污染均为0。不对无限个尚未开始的起点作无穷并合。

## 5. 错误候选排除概率

对某固定错误候选 \(\vartheta'\)，令
\[
R_t(\vartheta')=p_{\vartheta',t}/p_{\star,t}.
\]
每拍 \(\sqrt{R_t/R_{t-1}}\) 在真模型下的条件均值为两条件核的亲和度。如果在一段有 \(m\) 拍当前注入幅值均有规定分离，其他拍亲和度只用不超过1，则迭代条件期望给
\[
\mathbb E_\star\sqrt{R_t(\vartheta')}\le a^m.
\]
由 \(q_t\ge\pi_\star p_{\star,t}\)，\(\vartheta'\in C_t\) 蕴含
\(R_t>\varepsilon\pi_\star\)。Markov 给
\[
\boxed{
P_\star(\vartheta'\in C_t)
\le\frac{a^m}{\sqrt{\varepsilon\pi_\star}}.
}
\tag{17}
\]

固定真幅值 \(b^\star\)，定义
\[
a_0=\sup\mathcal A(K_{d_1,b^\star},K_{d_2,0})<1,
\]
\[
a_{\rm diff}
=\max_{b_j\ne b^\star}\sup\mathcal A(K_{d_1,b^\star},K_{d_2,b_j})<1,
\qquad \bar a=\max\{a_0,a_{\rm diff}\}<1.
\tag{18}
\]
上确界均在式(4)的共同紧集；若 \(J=1\) 没有 \(a_{\rm diff}\)，只取 \(\bar a=a_0\)。

晚起点错误幅值候选在自己起点前的当前注入为0，不能将它在整段真攻击期都误写成 \(b_j\)。但是真幅值 \(b^\star\) 对0也有分离，所以式(18)使用 \(\bar a\) 后，它在真起点以后的**每一拍**均有亲和度不超过 \(\bar a\)。这才合法地得到完整真攻击长度的指数。

## 6. 显式污染功能收缩定理

设 \(t\ge k^\star\)，真攻击至当前共
\[
n=t-k^\star+1
\]
个动作/载荷观测。任取整数 \(1\le L\le n\)，定义旧起点截断 \(s=t-L+1\ge k^\star\)。

把所有当前候选分成：

1. **好候选：** 幅值 \(b^\star\)，起点 \(k\le s\)。两候选至少最近 \(L\) 拍注入相同。从后验污染差递推及 \(0\le\theta\le B\) 得
   \[
   |\theta_t(k,b^\star)-\theta_t^\star|\le B\rho^L.
   \tag{19}
   \]
   不需要从中识别哪个起点正确。
2. **错误幅值、已经启动：** \(b_j\ne b^\star\)、\(0\le k\le t\)，共 \((J-1)(t+1)\) 个。由式(17)/(18)，每个保留概率至多 \(\bar a^n/\sqrt{\varepsilon\pi_\star}\)。
3. **同幅值但最近才启动：** \(k=s+1,\ldots,t\)，共 \(L-1\) 个。候选在 \(k^\star,\ldots,k-1\) 仍健康，分离拍数 \(k-k^\star\ge n-L+1\)，故保留概率至多 \(a_0^{n-L+1}/\sqrt{\varepsilon\pi_\star}\)。
4. **尚未启动/健康等价类：** 统一只计一次。它在真攻击后全部 \(n\) 拍当前注入均为0，所以保留概率至多 \(a_0^n/\sqrt{\varepsilon\pi_\star}\)。

因此至少有以下显式保留失败概率：
\[
\boxed{
\varepsilon_{t,L}
=\min\!\left\{1,
\frac{(J-1)(t+1)\bar a^n+(L-1)a_0^{\,n-L+1}+a_0^n}
{\sqrt{\varepsilon\pi_\star}}\right\}.
}
\tag{20}
\]
最近起点项也可用更紧的有限几何和
\(\sum_{j=1}^{L-1}a_0^{n-L+j}\) 代替。式(20)不要求事件独立。

除了概率至多 \(\varepsilon_{t,L}\) 的坏候选保留事件外，\(C_t\) 只含好候选。在全时域覆盖事件上，真候选属于 \(C_t\)，所以集合非空且其下确界不大于真污染。结合式(19)得到
\[
\boxed{
P_\star\{\theta_t^\star-B\rho^L\le L_t\le\theta_t^\star\}
\ge1-\varepsilon-\varepsilon_{t,L}.
}
\tag{21}
\]
若下界左端为负，它只是一个空泛下界，可与0取最大值。对上确界同理有
\(U_t\le\theta_t^\star+B\rho^L\)，所以同一事件上污染置信集合直径至多 \(2B\rho^L\)。

取 \(L_n\to\infty\)、\(L_n=o(n)\)，固定 \(k^\star\) 下有
\[
B\rho^{L_n}\to0,\qquad \varepsilon_{t,L_n}\to0.
\]
并且式(20)的失败界可求和：最终 \(n-L_n\ge n/2\)，其多项式因子乘指数尾可求和。因此 Borel–Cantelli 保证坏候选只被保留有限次，几乎处处成立；再与全时域覆盖事件相交，可得
\[
P_\star\{0\le\theta_t^\star-L_t\to0\}\ge1-\varepsilon.
\tag{22}
\]
表达式“\(0\le\theta_t^\star-L_t\to0\)”在此指所有时刻下界有效且差值趋零。它不是宣称 \(\theta_t^\star\) 本身收敛到一个正数，污染可以随事件继续波动。

式(14)与式(21)/(22)并不冲突：旧起点之间无限历史可区分信息有限，但它们对**当前污染函数**的影响同时消失。当前功能集合可以收缩，而起点集合不必收缩成单点。

## 7. 有用认证阈值：不是任意 \(g\) 都能保证到达

定义 \(\tau_{\rm safe}(g)=\inf\{t:L_t^2\ge g\}\)。仅有式(22)并不能保证任意预先给定的 \(g>0\) 及时达到；例如 \(g>B^2\) 不可能，而且长静默段会让真污染下降。

但在当前持续正向攻击下，真实发送时
\[
\theta_t^\star\ge k_- b^\star,
\]
并且给定事件前历史（包括已知中心），
\[
P_\star(\gamma_t=1\mid\text{事件前历史})
\ge p_s:=1-(1+ZS_-)^{-1/2}>0.
\tag{23}
\]
若
\[
0<g<(k_-b^\star)^2,
\]
可选固定整数 \(L\) 使
\[
B\rho^L\le k_-b^\star-\sqrt g.
\tag{24}
\]
在任何时刻同时有覆盖、无坏候选保留及真实发送时，式(21)/(24)就给 \(L_t^2\ge g\)。

设窗口从 \(T_0\ge k^\star+L-1\) 起、共 \(M\) 拍。迭代条件发送概率界给无发送概率不超过 \((1-p_s)^M\)。因此
\[
\boxed{
P_\star\{\tau_{\rm safe}(g)>T_0+M-1\}
\le \varepsilon
+\sum_{s=T_0}^{T_0+M-1}\varepsilon_{s,L}
+(1-p_s)^M.
}
\tag{25}
\]
可以再与1取最小值。这是与工程收益阈值有关的显式充分界：既包含污染功能排除速度，也包含得到一次足量注入/发送的机会，而不是仅说“检测器会报警”。

对固定 \(L\)，\(\sum_t\varepsilon_{t,L}<\infty\)；式(23)保证无限持续攻击下发送无限次几乎处处发生。因此，在至少 \(1-\varepsilon\) 的全时域覆盖事件上，满足上述严格阈值限制的 \(\tau_{\rm safe}(g)\) 最终有限。这里没有认证 \(a_0,\bar a\) 的具体数值，故尚不能声称某个工程阈值能在512拍内达到，也没有证明连续幅值置信集合具有同一速率。

## 8. 本轮可声明的结果与未完成项

可保留：精确中心/连续载荷记录下的幅值统一分离；同幅值固定起点的有限总KL和二元错误正下界；在有限反演幅值字典及精确混合参考下，式(20)–(22)的污染功能收缩；以及满足式(24)的有用校正阈值到达界。

本文件本身未完成连续幅值收缩或数值效率证明。后续[07](07_explicit_separation_and_expected_gain.md)给出显式但很保守的分离常数，[08](08_continuous_functional_contraction.md)给出稠密参考下连续幅值的存在性收缩，[03](03_continuous_amplitude_certificate.md)给出区间原型。实际认证速度、模型失配/有限字长保证和恢复后MSE性能实验仍未完成。本文件不把标准Hellinger、Ville、Bretagnolle–Huber或二次风险优化单独列为原创原理。
