# Task 1.2：固定模式传播矩阵及其停止时刻

## 1. “相同模式”与“相同年龄”不是同一假设

**DERIVED。** 设两臂使用相同y和K；定义h=hatX^a−hatX^0、b=m^a−m^0、γ^-=c^{a,-}−c^{0,-}，连续差向量 \(d_c=\operatorname{col}(h,b,\gamma^-)\)。

若从共同初始历史出发直到k均有σ^a=σ^0，则发送时钟和接收时刻也相同，raw缓存对齐差可写成A^aΔq。若此前已经分叉、只是当前都静默，年龄一般仍不同，不能作这一简化。即使年龄不同，对齐坐标γ^-的以下共同模式递推仍成立，因为它已包含年龄影响。

## 2. 显式M与B

令J为sender复制矩阵，\(J\hat X=\operatorname{col}_e\hat x_{\mathrm{src}(e)}\)；V为入边求和矩阵（每非零块为I2）。置
\[
S=\operatorname{diag}_i(\sigma_i I_2),\quad
R=\operatorname{diag}_e(\rho_e I_2),\quad
A_E=I_E\otimes A,\quad L=(I_N\otimes A)V,
\]
\[
F_k=\operatorname{diag}_i(A-K_i(k)H_i-\varepsilon \deg_i A).
\tag{3.1}
\]
这里R是刷新选择矩阵，不是量测噪声R_i。

同一模式下，从02的单拍映射相减：
\[
\gamma^+=RJh+(I-R)\gamma^-+Ru,\quad
h'=F_kh+\varepsilon L\gamma^+,\quad
b'=Sh+(I-S)b,\quad
\gamma^{-\prime}=A_E\gamma^+.
\tag{3.2}
\]
u是两臂载荷额外输入差，健康臂为0。矩阵为
\[
M_\sigma(k)=
\begin{bmatrix}
F_k+\varepsilon LRJ&0&\varepsilon L(I-R)\\
S&I-S&0\\
A_ERJ&0&A_E(I-R)
\end{bmatrix},\qquad
B_\sigma=
\begin{bmatrix}\varepsilon LR\\0\\A_ER\end{bmatrix},
\quad d_c'=M_\sigma(k)d_c+B_\sigma u .
\tag{3.3}
\]
M为40×40，B为40×20，包含估计10、发送参考10、对齐缓存20个分量。公式中的u只在已发送边有效，不可在静默边强行注入。

时钟差λ=ℓ^a−ℓ^0、η=τ^a−τ^0在共同模式下分别按(1−σ)、(1−ρ)保留或清零。共同历史使其恒为0；它们是整数状态，不是连续Gaussian攻击量。

## 3. 首次单包Replay

**命题的局部引理（DERIVED）。** r前两臂初值、物理噪声、量测、发送/缓存状态相同；r当拍0真实发送；仅边0→1的raw载荷从hat_x_0(r)替换成hat_x_0(s)，s为真实过去发送；原Yang无门控、无裁剪。则
\[
h_1(r+1)=\varepsilon A\delta_r,\quad h_i(r+1)=0\ (i\ne1),
\quad b(r+1)=0,\quad
\gamma_{e*}^-(r+1)=A\delta_r,
\tag{3.4}
\]
其他γ块为0，时钟差为0。

**证明。** r的hatX/m/时钟一致，故发送判决一致且已经完成；发送端参考存真实hatX，不写入攻击载荷，所以b'=0。新包age0导致γ_e*^+=δ；其余边γ^+=0。本地预测/量测项逐项相消，唯一不同一致性项为εAδ，仅进入receiver1；下一拍旧缓存外推乘A。证毕。

失效边界：门控/裁剪、改变y/物理状态、未实际发送、r前已有污染，或者把raw历史包先外推再替换，均不满足该引理。δ=0时全部污染为0；不应删掉这种合法但无效载荷差。

## 4. 多步传播和首次分叉的正确端点

定义全网首次发送模式分叉
\[
\kappa=\inf\{k>r:\sigma^a(k)\ne\sigma^0(k)\}.
\]
单包其后u=0；对r+1≤k≤κ，
\[
d_c(k)=\Phi(k,r+1)d_c(r+1),\qquad
\Phi(k,t)=M_\sigma(k-1)\cdots M_\sigma(t).
\tag{3.5}
\]
κ时刻**进入发送判决前的状态**仍由共同分支传播给出；κ当拍判决不同，因此不能用共同M预测κ+1。若κ不存在，(3.5)适用于整个观察域。前稿“只能k<κ”的写法过窄，正确边界是可到pre-decision κ，但不能跨越其更新。

**DERIVED。** 每次M随时刻增益和模式变化，固定模式指同一条模式序列，不一定σ在时间上恒定。不能把共同模式分析写成一个时间不变M，更不能将两个臂事后强制共享健康schedule后叫真实闭环响应。

## 5. 核验层次

历史首次注入：从Task0.5保存的δ与观测差独立复算(3.4)，无需读原NPZ或重生噪声。人工代数：用冻结A/H/ε及由历史gain公式独立手算的k=0,K_i(0)构造任意二维矩阵fixture，检查(3.2)的逐节点计算等于(3.3)块矩阵；这些fixture只检验恒等式，不是实际r≈200的增益或新系统轨迹。详细结果见07和code/task1_formula_checks.py。
