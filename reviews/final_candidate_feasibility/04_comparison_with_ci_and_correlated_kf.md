# 04 与CI、相关噪声KF及其余基线的严格比较

日期：2026-11-14。所有结论针对02号固定线性融合与有效总体原始矩；条件版本需另外给出同一信息集下有效条件矩。以下证明是DERIVED / STANDARD，不能作为新方法创新。

## 1. 统一问题

两份在线可算估计误差为e、f，权重λ：

\[
\hat x_\lambda=(1-\lambda)\hat x_1+\lambda\hat x_2,\quad
J=(1-\lambda)^2p+\lambda^2r+2\lambda(1-\lambda)c,
\tag{C1}
\]

\[
p=\mathbb E e^2,\quad r=\mathbb E f^2,\quad c=\mathbb E ef.
\]

可直接取03号M18的Yang两份下一拍候选，不需换估计器。允许均值非零；P/R必须包含已传播的攻击损伤，不能用健康名义协方差。

所有比较明确区分“实际模型可达矩集合”和“只知道边际矩的PSD外包”。证明外包上最优不等于证明每个外包点都可由一个完全指定的Yang模型实现。

## 2. 仅有边际信息：精确minimax与CI一致

令

\[
\mathscr U_{\rm marg}=
\left\{(p,r,c):0\le p\le P,\ 0\le r\le R,\
\begin{bmatrix}p&c\\c&r\end{bmatrix}\succeq0\right\},\quad P,R>0.
\]

**命题C1（PROVED / STANDARD）。** 对任意确定实数λ，

\[
\sup_{\mathscr U_{\rm marg}}J(\lambda)
=\left(|1-\lambda|\sqrt P+|\lambda|\sqrt R\right)^2,
\tag{C2}
\]

\[
\inf_{\lambda\in\mathbb R}\sup_{\mathscr U_{\rm marg}}J(\lambda)
=\min(P,R).
\tag{C3}
\]

证明：Cauchy–Schwarz给 \(|c|\le\sqrt{pr}\)。令 \(e=\sqrt P Z,f=\pm\sqrt RZ,\mathbb E Z^2=1\)，按权重乘积选符号，达到C2。又

\[
|1-\lambda|\sqrt P+|\lambda|\sqrt R
\ge\min(\sqrt P,\sqrt R)(|1-\lambda|+|\lambda|)
\ge\min(\sqrt P,\sqrt R).
\]

λ=0或1中较优端点达到等号，得到C3。无均值/独立/Gaussian假设。

标量CI为

\[
P_{\rm CI}(\omega)=
(\omega/P+(1-\omega)/R)^{-1},\quad 0\le\omega\le1,
\tag{C4}
\]

对应权重 \(1-\lambda=P_{\rm CI}\omega/P\)，
\(\lambda=P_{\rm CI}(1-\omega)/R\)。其最优证书同样是 \(\min(P,R)\)。

因此：

- P<R时，任意正邻居权重在C2外包上都严格差于P；
- P=R时，凸权重可非零，但只能保持最坏风险P，不能严格改善；
- R<P时可以采用邻居降低风险，CI已能选择较优输入。

这并不禁止已知动态模型额外收紧集合；它精确说明“仅边际矩+缓存存在”不足以声称严格优势。

## 3. 严格优于标量CI需要哪条额外约束

进一步**合法认证**

\[
c\le C,\quad -\sqrt{PR}\le C\le\sqrt{PR},
\quad \mathscr U_C=\mathscr U_{\rm marg}\cap\{c\le C\}.
\tag{C5}
\]

对凸权重，矩阵 \(\begin{bmatrix}P&C\\C&R\end{bmatrix}\)可行，且p、r、c的系数非负，故

\[
\sup_{\mathscr U_C}J(\lambda)
=(1-\lambda)^2P+\lambda^2R+2\lambda(1-\lambda)C.
\tag{C6}
\]

**命题C2（PROVED / STANDARD）。** 存在内点λ严格优于最优标量CI的充要条件是

\[
\boxed{C<\min(P,R)}.
\tag{C7}
\]

证明：不妨P≤R。C6减P：

\[
2\lambda(C-P)+\lambda^2(P+R-2C).
\]

二次项系数非负。C≥P时没有严格改善；C<P时小正λ严格改善，最优值

\[
\lambda_*=\frac{P-C}{P+R-2C}\in(0,1),\quad
\bar J_C(\lambda_*)=\frac{PR-C^2}{P+R-2C},
\tag{C8}
\]

\[
P-\bar J_C(\lambda_*)=
\frac{(P-C)^2}{P+R-2C}>0.
\tag{C9}
\]

对称得到C7。这个证明适用于参数区域，不是展示一个有利数值点。

**重要限制：** \(\mathscr U_C\subsetneq\mathscr U_{\rm marg}\)只要求C<√PR，而严格风险改善还需C<min(P,R)。集合变小并不必然有更低最坏风险。若P、R、C来自同一不确定参数的不同上界，C6仅是外包精确式，未必是更窄真实参数曲线上的精确最坏值。

C8是标准相关感知二次风险/minimax权重。若候选只能实现C5—C8，按负责人标准仍非独立创新；必须另有不可替代的新操作和合法来源。缓存低秩本身不给出C7。

## 4. 五个基线逐项比较

|基线|实际使用的信息/操作|可保证对象|对当前候选的判定|
|---|---|---|---|
|正确相关噪声KF/增广估计|包扰动作为同一潜变量；所有已知时间/节点交叉矩保留|联合线性Gaussian且分布已知时为条件MMSE；一般已知二阶矩时为LMMSE，不泛称非Gaussian最优|已直接处理同包复用，不能把增广矩传播列为新操作|
|独立噪声近似|丢弃交叉项或把同包当新样本|通常只得到错误报告方差，无覆盖保证|可以被05号整个参数族反驳；打败它不满足强基线门槛|
|协方差膨胀|Young/Cauchy–Schwarz处理未知相关，03号M15/M16即同类|有效原始边际界下有限保守上界|这是已有工具，不是新机制；若也用合法结构，应允许它先收紧边际界|
|CI|有效边际矩，交叉任意未知；C4|对所有允许相关性一致保守，优化标量风险C3|缓存相关不会使CI失效；严格改善必须有额外有效约束|
|Oracle真实联合矩融合|真实均值、完整误差/隐私/攻击联合矩，非真实噪声实现值|确定权重类最优风险；有完整Gaussian条件模型时等于正确相关KF|额外信息基准，不可部署；不能由其优势宣称当前接收端可实现|

### 4.1 正确相关KF与oracle

若真实原始p、r、c已知，C1无约束最优权重为

\[
\lambda_o=\frac{p-c}{p+r-2c}.
\tag{C10}
\]

分母为 \(\mathbb E(e-f)^2\)，为0时两估计几乎处处相同，没有新信息。限制凸融合时将权重限制在[0,1]；有已知偏置时，可先做标准仿射均值校正，再以中心矩优化。不能在未知偏置时免费使用这种校正。

等价创新形式 \(\hat x^+=\hat x_1+K(\hat x_2-\hat x_1)\) 满足

\[
K=\frac{\mathbb E[e(\hat x_2-\hat x_1)]}
{\mathbb E[(\hat x_2-\hat x_1)^2]}
=\frac{p-c}{p+r-2c}.
\tag{C11}
\]

这就是相关噪声线性估计的常规更新。未知矩、任意有界非Gaussian攻击时不能声称普通KF自动给精确条件MMSE；需保留不确定矩并使用标准鲁棒界。

### 4.2 膨胀与CI包络

对0<ω<1，Young界为

\[
J(\lambda)\le
\frac{(1-\lambda)^2P}{\omega}
+\frac{\lambda^2R}{1-\omega}.
\tag{C12}
\]

对ω优化得到C2，进一步对λ优化得到C3。所以在相同边际信息下，“最优膨胀”也不会产生严格超CI的证书。固定任意膨胀常数可能更差；不能以其随意保守设定制造方法优势。

### 4.3 独立近似不构成有效强基线

假设c=0会给 \(\lambda=P/(P+R)\) 和报告风险PR/(P+R)。但允许c=√PR时实际风险多出
\(2\lambda(1-\lambda)\sqrt{PR}\)。P=R时它报告P/2而真实可为P。05号进一步给包含新本地量测的精确缓存反例族。

## 5. 缓存结构何时收紧集合，如何计算

轨迹约束 \(L\Sigma_\xi L^T\) 确实排除了任意逐时隐私矩，所以轨迹集合可能严格小于“不知道同一包身份”的集合。但要投影到当前e、f风险，仍需其与基础误差/攻击的交叉块。

- 已认证完整联合模型：03号M10—M12合法离线计算，保留缓存反馈；结果属于标准增广相关估计。
- 已认证部分分块独立/交叉界：可形成更小集合，甚至满足C7；收益来自明确的额外联合信息，标准结构化矩融合可同样利用。
- 只有隐私方差区间、缓存年龄和未知发送误差/攻击相关：不能推出C7。若还缺有效边际P/R，连CI输入也不完整；新候选没有凭空补齐它们的机制。

**数学判定：** 已明确证明“什么额外条件可产生严格风险改善”，也明确其操作是标准相关感知融合。当前未出现超出现有工具的缓存专属操作，不能给GO。
