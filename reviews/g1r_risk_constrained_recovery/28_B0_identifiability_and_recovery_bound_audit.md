# G1-R-B0：历史 Replay 污染可恢复性与不可辨识性定理可行性审查

状态：只读数学与证据审计；供研究负责人审阅；不构成立项或算法变更。

本报告区分 **FACT**（材料/代码/数据直接支持）、**DERIVED**（由其推导）、**HYPOTHESIS**（待验证解释）与 **OPEN**（证据缺口）。数值矩阵分析仅读取已保存 NPZ 和 CSV，没有生成随机轨迹。报告不提交、不推送。

## 0. 基线和可复核范围

**FACT。** 指定仓库的隔离分支为 `g1r-e2-status-contract-20261115`，远端为 `center-666/paper`；当前 HEAD 是 `03a00789508755f1df9bf16dee901af37d7e34f1`，其父提交为指定基线 `9debe50360dc80bca0b3228351da65dc53709a0a`。HEAD 与任务书要求的精确 HEAD 不一致，是因为随后只新增并推送了 27 号可复用成果文档。未切换分支、未清理现场。

**FACT。** 主工作区 `C:\Users\zhongxin\shixidoc\mypaper` 仍在 `main`、HEAD `490e5b8...`，有多项 G5 未提交改动；本轮没有访问或修改这些改动。隔离工作区本轮开始前有一个上轮创建的未跟踪文件 `27_e3_postmortem_and_next_decision_draft.md`；保留不动。本轮新增文件仅为本报告。

**OPEN。** 任务要求的 `paperlast` 目录在当前隔离仓库不存在，搜索命令返回路径不存在。没有据此推断该仓库或 Zotero 中不存在文献；本轮仅使用当前仓库已有的直接竞争审计和可访问材料。用户要求的六个主题类别没有在本仓库找到可逐篇核查的专门全文集合，因此不能宣称完成了相应领域的完整文献调查。

## 1. 实际 G1-R 线性响应模型

### 1.1 代码/矩阵所对应的对象

**FACT。** [07_replay_joint_probability_model.md](07_replay_joint_probability_model.md) 第 1、3、4 节说明：Yang 仿真固定五节点、二维状态、gap-8 外生日程；目标接收节点为节点 1，目标时刻为 217；合法在线创新为

\[
z=\operatorname{col}(\nu_1(211),\ldots,\nu_1(216))\in\mathbb R^{12}.
\]

Replay 载荷参数 \(\theta_{h,a}\in\mathbb R^2\) 是事件 (h=(edge,r))、年龄 (a\in\{32,64,96\}) 对应的真实发送包与当前名义包之差。保存矩阵中的 `O[i]` 维数为 (12\times2)，`G[i]` 为 (2\times2)，并有

\[
z=\eta^0+O_{h,a}\theta_{h,a},\qquad
\Delta_{217}=G_{h,a}\theta_{h,a}.
\]

该式是相对同初始条件、过程噪声、量测噪声和发送日程的健康反事实创新/估计差，不是将全部创新视为独立白噪声。事件列表与全部矩阵存于 [replay_joint_matrices.npz](results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz)，摘要见 [07_replay_joint_probability_model.md](07_replay_joint_probability_model.md) 第 8 节。这里 (O,G) 可依年龄和目标时刻而异。

**FACT。** 参数 \(\theta\) 不是外生且与噪声独立的任意输入。它由发送端先前估计差构成，和健康创新噪声、健康目标误差相关。 [07_replay_joint_probability_model.md](07_replay_joint_probability_model.md) 第 3—5 节保存了共同原始噪声 loading `theta_loading`、`eta_loading`、`e0_loading` 及交叉协方差。固定候选条件下，

\[
\operatorname{Cov}(\theta,z)=\Sigma_{\theta\theta}O^T+C_{\theta\eta},
\]

\[
\Sigma_{zz}=\Sigma_\eta+O\Sigma_{\theta\theta}O^T
 +O C_{\theta\eta}+C_{\theta\eta}^T O^T,
\]

\[
\operatorname{Cov}(e_0,z)=C_{0\eta}+C_{0\theta}O^T.
\]

所以本报告的零噪声可辨识命题是结构命题；统计和风险推导必须保留这些相关项。

### 1.2 事件可辨识、影响可辨识、统计可辨识

**DERIVED。** 应区分三种概念。

1. **结构事件可辨识。** 无噪声映射下，解释集 (\mathcal Z_h=\{O_h\theta:\theta\in\Theta_h\})。在给定 (z) 下事件唯一，当且仅当 (z) 与至多一个 (\mathcal Z_h) 相交。若只比较一个确定参数解释，则要求不同事件的可行响应集合不重合。若参数未知且自由变化，满列秩 (O_h) 只保证固定 (h) 内的参数唯一，不保证不同事件的响应集合互不相交。
2. **目标影响可辨识。** 对所有与同一无噪声创新 (z) 相容的解释，(G_h\theta) 必须相同。事件可以不唯一而影响唯一；这是恢复污染所需的较弱条件。
3. **统计可辨识/不可区分。** 完整观测概率律 (P_h(z)) 必须区分。若存在同一参数化下两个假设给出完全相同的 (z) 分布，则从 (z) 无法统计地区分；均值响应接近或相同并不足够，因为协方差仍可能不同。若两个分布仅接近，属于有限样本难区分，不是严格统计不可辨识。

事件真值、年龄及攻击载荷标签只用于离线审计，不可输入在线补偿器。事件识别结论必须相对于这里明确的创新信息集作出，不能与使用更多接收日志的其他问题混同。

## 2. 跨事件核空间条件及参数域

令 (h,h'\) 两个候选、其参数域分别为 (\Theta_h,\Theta_{h'}\)。定义

\[
A_{hh'}=[O_h,-O_{h'}],\quad B_{hh'}=[G_h,-G_{h'}],\quad
v=\operatorname{col}(\theta,\theta').
\]

**DERIVED（无约束线性参数域）。** 若 (\Theta_h\times\Theta_{h'}) 是整个对应参数空间，所有观测相同解释都给出相同目标影响，当且仅当

\[
\ker A_{hh'}\subseteq\ker B_{hh'}
\quad\Longleftrightarrow\quad
\operatorname{rank}\begin{bmatrix}A_{hh'}\\B_{hh'}\end{bmatrix}
=\operatorname{rank}A_{hh'}.
\tag{1}
\]

等价地，存在矩阵 (L) 使 (B_{hh'}=LA_{hh'})。式 (1) 才是跨事件版本；单事件条件 (\ker O_h\subseteq\ker G_h) 不足以处理两个不同事件。该结论属于标准线性功能可辨识条件，G1 原报告 [04_theorem_candidates.md](../g1_retroactive_recovery/04_theorem_candidates.md) 的 T3 已经给出单事件版本；G1-R [02_mathematical_audit.md](02_mathematical_audit.md) 第 3 节也给出有限性条件。

**DERIVED（有界或受限参数域）。** 若真实域是严格子集 (\Theta_h\times\Theta_{h'}=\mathcal T_{hh'}\)，则全空间核包含可能过强。正确的必要充分条件是

\[
\forall v\in\mathcal T_{hh'}:\ A_{hh'}v=0\ \Rightarrow\ B_{hh'}v=0.
\tag{2}
\]

若要求只在任一有界集合对上可恢复，直接检查其差异集合与 (\ker A\) 的交集；例如盒约束、球约束或 Replay 来源可行域会排除某些线性核方向。不能把“有限幅值”仅作为数值裁剪后仍称全空间核条件是必要条件。

### 2.1 两种“事件不可辨但影响可辨”关系

**DERIVED。** 逻辑上，两种情况均可能：

- 同一 (z) 下有两个事件标签，但所有相容 (G_h\theta) 都相同，事件不可辨、影响可辨；
- 同一 (z) 下有两个事件标签且 (G_h\theta\ne G_{h'}\theta')，事件不可辨、影响也不可辨。

最小示例（均为确定性结构示例，不是 G1-R 实际参数）：取标量 (O_1=O_2=1)。令 (G_1=G_2=1)，同一 (z=1) 下两事件参数均为 1，则事件标签无法区分但目标影响均为 1，影响唯一。若改为 (G_1=1,G_2=2)，同一 (z=1) 下影响分别为 1 和 2，事件和影响都无法唯一恢复。若给第二例加独立 (N(0,\sigma^2)) 观测噪声，两事件的 (z\) 边际仍相同，但污染不同；任何只依赖 (z) 的单一动作都不能同时精确抵消两者。

**边界。** 这些示例验证命题之间的逻辑区别，不是论文原创定理，也不是当前五节点矩阵的数值实例。

## 3. 结构响应的只读矩阵分析

分析输入为 [replay_joint_matrices.npz](results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz)：8 个事件 × 3 年龄，共 24 个 (O,G,\Sigma_{zz}) 模型；E3 分层评价为 [event_age_metrics.csv](results/g1r_e3_completion_audit_20261116_r01/event_age_metrics.csv)。所有结论仅适用于这批已保存矩阵。

### 3.1 单事件秩与条件数

**DERIVED。** 对 24 个模型的 (O_{h,a}\) 做 SVD：每个矩阵的数值 rank 均为 2/2，故在无噪声、固定事件且自由二维参数下参数可唯一恢复。最小奇异值随事件由约 (0.00163) 到 (0.04163) 变化；`cond(O)` 范围约 1.21—3.03。不同年龄下同一事件的 (O) 相同，因为保存窗口和传播响应固定在该目标定义中；年龄变化主要改变参数生成/联合分布，不改变本次保存的线性 (O)。

**DERIVED。** 用每一模型对应的 (Sigma_{zz}) 计算条件数，范围约 3.56—382.67；随 Replay 年龄在后期事件上显著增大。它表示创新联合协方差的数值尺度/相关条件，不等同于“攻击响应不可辨识”。不能用该条件数直接解释 Set 拒绝或恢复性能。

### 3.2 跨事件核条件

**DERIVED。** 对每个年龄内 8 个事件的 28 对事件，构造 (A_{hh'}=[O_h,-O_{h'}]\) 与 (B_{hh'}=[G_h,-G_{h'}]\)。所有 84 个事件—年龄对比的 (A) 数值 rank 均为 4/4，联合 rank ([A;B]\) 也均为 4/4。因此在未约束实参数空间的线性模型中，(1) 对这 84 对成立；而且 (A v=0) 只允许 (v=0)，所以并不存在非零参数产生相同创新响应的跨事件冲突解释。

**DERIVED。** 这不是新的“目标影响更容易识别”结构优势：在这些矩阵上，给定相同 (z-\eta^0) 的不同事件/参数已经被完整 (O) 响应分开。核条件成立是因为跨事件堆叠 (A) 满列秩，而非一个独特的 (G)-相对-(O) 投影关系。

**重要限制。** 数值 rank 依赖浮点秩阈值，报告中的全满秩是双精度矩阵上的计算结论。需进行符号/高精度核验才能声称精确秩；当前不需要该额外核验，因为本轮目标是可行性审查，且现有数值已未显示可用的特殊跨事件零空间。不能把矩阵满秩等同于有限噪声下容易统计识别。

### 3.3 受限参数域

**OPEN。** 保存的 `theta_loading` 和事件来源规则支持每个候选的 Gaussian 参数分布，但没有保存“所有合法攻击幅值/Replay 源组成的确定性可行集合”及其物理边界。因而本轮不能对 (2) 的受限域交集进行完整几何审计，也不能把模拟生成的概率支撑未经核实地等同于攻击者可行域。

**DERIVED。** 由于无约束跨事件 (A) 在数值上满列秩，即使真实域受限，也不会从当前矩阵得到“不同事件在精确无噪声创新上重合、但目标影响不同”的非平凡两点例子。噪声存在时的重叠应转到统计分布和有限样本风险分析，而不是把数值精度误称为结构不可辨识。

## 4. 联合 Gaussian 统计可辨识

### 4.1 完整 Gaussian 模型

**FACT。** [07_replay_joint_probability_model.md](07_replay_joint_probability_model.md) 第 3—5 节在每个固定事件/年龄下把 \((\theta,\eta^0,e_0)\) 写成同一原始 Gaussian 向量的线性变换，没有假设相互独立。令

\[
z=O\theta+\eta,\quad \Delta=G\theta,
\]

并记

\[
V_\theta=\operatorname{Cov}(\theta),\quad C_{\theta\eta}=\operatorname{Cov}(\theta,\eta),\quad
C_{e\theta}=\operatorname{Cov}(e_0,\theta),\quad C_{e\eta}=\operatorname{Cov}(e_0,\eta).
\]

本冻结模型均值为零，协方差块为

\[
\Sigma_{zz}=\Sigma_\eta+OV_\theta O^T+OC_{\theta\eta}+C_{\theta\eta}^TO^T,
\]

\[
\Sigma_{e z}=C_{e\eta}+C_{e\theta}O^T,
\qquad
\Sigma_{e\Delta}=C_{e\theta}G^T.
\]

若联合 Gaussian 且 \(\Sigma_{zz}\succ0\)，则

\[
E[e_0\mid z]=\Sigma_{ez}\Sigma_{zz}^{-1}z,
\]

\[
\operatorname{Cov}(e_0\mid z)=\Sigma_{ee}-\Sigma_{ez}\Sigma_{zz}^{-1}\Sigma_{ze}.
\]

对真实误差 (e=e_0+\Delta)，以

\[
\Sigma_{ez}^{*}=\operatorname{Cov}(e_0+\Delta,z),\qquad
\Sigma_{ee}^{*}=\operatorname{Cov}(e_0+\Delta)
\]

替换，即可得到 (E[e\mid z]) 和条件协方差。所有交叉块应从联合 loading 构造；若只使用 \(O\theta\) 均值而将 \(\theta\) 与 \(\eta\) 独立，会改变 (P_h(z))。

### 4.2 固定参数与随机 Replay 参数不能混用

**DERIVED。** 对“固定给定 (h,\theta)”的条件模型，

\[
z\mid h,\theta\sim N\bigl(O_h\theta+E[\eta\mid h,\theta],\ 
\Sigma_{\eta\eta\mid\theta,h}\bigr).
\]

若 \((\eta,\theta)\) 联合 Gaussian，且 \(\Sigma_{\theta\theta}\) 可逆（否则用支持空间上的广义逆并要求一致性），则

\[
E[\eta\mid\theta]=C_{\eta\theta}\Sigma_{\theta\theta}^{\dagger}\theta,
\]

\[
\Sigma_{\eta\eta\mid\theta}
=\Sigma_\eta-C_{\eta\theta}\Sigma_{\theta\theta}^{\dagger}C_{\theta\eta}.
\]

因此“固定 \(\theta\) 后均值就是 (O_h\theta)，协方差就是健康噪声协方差”只有在相应零交叉协方差条件下才成立。Replay 参数源自历史估计差，一般不应默认该条件。该相关性边界亦见 [cross_phase_identifiability_audit/03_identifiability_and_statistics.md](../cross_phase_identifiability_audit/03_identifiability_and_statistics.md) 第 6 节。

对本项目实际使用的“事件/年龄随机参数先验”边际分布 (z\mid h,a\) 为零均值 Gaussian，协方差是保存的 Σ_zz。两个假设边际分布相同，当且仅当其均值和协方差都相同（支持空间退化情形需比较特征函数/支撑空间）。只比较 (O_h\theta) 或其均值不足以判定统计不可辨识。

### 4.3 KL 与统计距离

**DERIVED。** 对两个非退化 Gaussian (P_1=N(\mu_1,S_1))、(P_2=N(\mu_2,S_2))，

\[
D_{KL}(P_1\|P_2)=\frac12\left[
\operatorname{tr}(S_2^{-1}S_1)+(\mu_2-\mu_1)^TS_2^{-1}(\mu_2-\mu_1)-d
+\log\frac{\det S_2}{\det S_1}
\right].
\]

严格统计不可区分等价于 (\mu_1=\mu_2,S_1=S_2)（或两退化 Gaussian 的均值和协方差相同）。若协方差相同且均值差为 (d_\mu)，KL 为 (\frac12d_\mu^TS^{-1}d_\mu)。若均值相同但协方差不同，KL 通常大于零，故均值响应相同不代表统计不可辨识。

### 4.4 保存矩阵的分布距离复核

**DERIVED。** 对同年龄 28 对候选的边际 (N(0,\Sigma_{zz,h,a}))，计算双向 KL 的平均（Jeffreys 对称化值）。各年龄范围为：

| Replay 年龄 | 对数 | 对称 KL 最小值 | 中位数 | 最大值 |
|---:|---:|---:|---:|---:|
| 32 | 28 | 0.0000820 | 0.66388 | 15.7256 |
| 64 | 28 | 0.0006293 | 2.01006 | 46.6359 |
| 96 | 28 | 0.0015858 | 3.08076 | 78.3781 |

在这些有限矩阵对中，没有协方差完全相同的事件对；部分分布很接近，部分分离明显。这个结果只反映冻结 Gaussian 边际模型的候选分布距离，不是事件识别准确率，也不证明实际 Hard/Soft/Set 的统计功效。

## 5. 恢复风险下界

### 5.1 结果 A：污染残差的两点和多点下界

**DERIVED（两点命题）。** 固定一个在线观测 (z)，设两个相容解释的目标影响分别为 (\Delta_1,\Delta_2)。任何确定性补偿器在该 (z) 必须输出同一个 (u(z))。由三角不等式，

\[
\max\{\|\Delta_1-u\|,\|\Delta_2-u\|\}
\ge\frac12\|\Delta_1-\Delta_2\|.
\tag{3}
\]

**证明。** 若两项都小于右端，二者相加会给出 (\|\Delta_1-\Delta_2\|<\|\Delta_1-\Delta_2\|)，矛盾。等号由两点中点达到。该结论可扩展到带权范数，但它是标准两点 minimax/Chebyshev 半径，不是新算法或当前模型的额外性质。

对多解释集合 (D(z))，污染残差最小最坏值为

\[
\inf_u\sup_{\Delta\in D(z)}\|\Delta-u\|,
\]

即 (D(z)) 的最小包围球半径（在非闭有界集合取闭包；无界时半径无穷）。任何 (u(z)) 的最坏污染残差至少为 (\operatorname{diam}(D(z))/2)。污染唯一恢复当且仅当 (\operatorname{diam}(D(z))=0)。该几何量描述估计污染，不是状态误差或 MSE。

### 5.2 结果 B：真实 MSE 与 Oracle regret

令解释 (i\) 下条件真实目标误差为 (e_i=e_0+\Delta_i)。给定相同合法观测 (z)，定义

\[
m_i(z)=E[e_i\mid z,i],\qquad V_i(z)=\operatorname{Cov}(e_i\mid z,i).
\]

对共同动作 (u(z))，

\[
E[\|e_i-u\|^2\mid z,i]
=\operatorname{tr}V_i+\|m_i-u\|^2.
\tag{4}
\]

若能知晓真实解释，条件平方损失 Oracle 的最优动作为 (u_i^*(z)=m_i(z))，Oracle 条件风险为 \(\operatorname{tr}V_i\)。共同动作相对解释 (i) 的 regret 为

\[
\mathcal G_i(u\mid z)=\|u-m_i(z)\|^2.
\tag{5}
\]

若两个解释对在线观测给出完全相同的 (z)（确定性同一观测或条件分布相同且使用同一可观测 (z) 规则），则任意共同动作满足

\[
\max_i\mathcal G_i(u\mid z)
\ge \frac14\|m_1(z)-m_2(z)\|^2.
\tag{6}
\]

**证明。** 将 (3) 应用于两个 Oracle 目标 (m_1,m_2) 并平方。若条件协方差相同，最坏条件真实 MSE 至少为

\[
\operatorname{tr}V+\frac14\|m_1-m_2\|^2.
\]

若 (V_1\ne V_2)，相对各自 Oracle 的 regret 下界 (6) 仍成立，因为 (4) 的协方差项在同一解释与其 Oracle 风险相减时抵消；绝对最坏风险下界则应写成

\[
\inf_u\max_i\{\operatorname{tr}V_i+\|m_i-u\|^2\},
\]

不能简单写为 (\max_i\operatorname{tr}V_i+\|m_1-m_2\|^2/4)，除非进一步满足等协方差或其他可证明条件。

**关键限制。** 污染差 \(\Delta_1-\Delta_2\) 不能直接替代真实条件均值差 (m_1-m_2)。其中

\[
m_i(z)=E[e_0\mid z,i]+\Delta_i(z),
\]

若 (e_0) 与 Replay 参数/创新相关，不同假设还可能改变 (E[e_0\mid z,i])。所以污染残差下界不自动推出真实 MSE 下界；式 (6) 必须使用完整联合 Gaussian 条件均值，不能忽略健康误差交叉项。

### 5.3 结果 C：多解释集合与风险

**DERIVED。** 对给定 (z) 定义污染集合

\[
D(z)=\{G_h\theta:\ (h,\theta)\text{ 与 }z\text{ 相容且属于合法参数域}\}.
\]

若 (D(z)) 有限直径，则污染恢复不可避免的最坏误差下界至少为 (\operatorname{diam}(D(z))/2)。若用条件真实误差均值集合

\[
M(z)=\{E[e_0+G_h\theta\mid z,h,\theta]\},
\]

则共同动作相对条件 Oracle 的最坏 regret 至少为 (\operatorname{diam}(M(z))^2/4)（欧氏平方损失）。这一区分给出一条严格边界：只有在可行解释对同一观测有相同似然/条件化规则时，才可将各解释共同动作比较；若观察分布不同，决策器可利用 (z) 的概率证据，不能假定它面对完全相同的信息。

**OPEN。** 当前项目没有定义基于连续噪声观测的“硬相容”集合 (D(z)) 为哪些解释；E2 的统计置信椭球并集是带校准阈值的置信集合，不是确定性可行集合，也不是后验支持集。把 (3)/(6) 用到 E2 的集合前必须指定相容置信水平、覆盖失败事件损失上界以及条件/无条件风险目标。当前无此完备转接定理。

## 6. 与既有 E3 的只读联系

### 6.1 已观察到的配对数据事实

**FACT。** E3 以 Seed 为统计单位，8 事件和 3 年龄均配对。Set 的 3605/4800 Replay 场景为 `ZERO_OR_UNRESOLVED`，没有求解器失败；主场景动作率 142/200。主场景 Set MSE 9.661847，相对 Yang 改善 2.40194%，但高于 Hard 的 9.656828 和 Soft 的 9.654265。age64 最坏事件风险比较的 Set 余量对 Hard 为 -0.20374462、对 Soft 为 -0.20320702，单侧 97.5% 整 Seed Bootstrap 下端点均为负，最终为 `NO_GO_PERFORMANCE`。出处是 [26_e3_formal_experiment_report.md](26_e3_formal_experiment_report.md) 第 3—9 节；完整 Seed 配对分层数据见 [event_age_metrics.csv](results/g1r_e3_completion_audit_20261116_r01/event_age_metrics.csv)。

### 6.2 确定性指标和事件—年龄描述关系

**DERIVED / EXPLORATORY。** 将矩阵 (\sigma_{min}(O_h))、(\kappa(\Sigma_{zz,h,a})) 与 24 个 E3 事件—年龄聚合单元合并，只作探索性描述：

- Set 非零动作率与 (\sigma_{min}(O)) 的 24 单元 Pearson 相关约 0.870；
- Set 非零动作率与 (\kappa(\Sigma_{zz})) 的相关约 0.789；
- Set-Hard MSE 差与上述 (\sigma_{min}(O)) 的相关约 0.271；
- Set-Soft MSE 差与上述 (\sigma_{min}(O)) 的相关约 0.213。

这些只是 24 个高度结构相关的事件—年龄汇总单元，不是独立统计样本，未作显著性检验，不能作为确认性发现。尤其 (O) 的 (\sigma_{min}) 与攻击幅度/目标损失规模、事件位置共同变化，相关不能解释因果。

**DERIVED。** 描述性格局是：早期事件 ((0,176),(3,178)) 上 (\sigma_{min}(O)) 较小、Set 动作率约 0.5%，后期事件动作率较高；这与“早期事件创新响应弱、Set 更常拒绝”的假设一致，但 E3 的 `ZERO_OR_UNRESOLVED` 可能同时来自集合含零、候选冲突、门限拒绝等机制，当前没有逐原因字段的完整分解。

**OPEN。** 要作 Seed 配对的正式机制分析，需要每个 Seed—事件—年龄的具体集合几何（直径、零是否在凸包、Chebyshev 中心、真影响与中心误差、gate 前分数）及与 proposal 的稳定 join key。当前 E3 聚合 CSV 不含这些量；E2/Run 记录有部分 proposal 状态和动作，但现有证据没有完成上述几何量与全 Seed 真实损失的配对表。本轮不重跑集合构造、不重新运行算法。

### 6.3 损失分解

**FACT。** 对方法动作 (u(z))，逐样本攻击真实 MSE 改善恒等式是

\[
L_a-L_a^u
=\underbrace{(2\Delta^Tu-\|u\|^2)}_{\text{污染收益}}
+\underbrace{2e_0^Tu}_{\text{健康误差交叉项}}.
\]

净恢复收益还要减去配对健康场景收益基准 (E[L_0-L_0^u])。E3 主场景 Set 的攻击 MSE 收益 0.23778329，由污染收益 0.23556171 和健康交叉项 0.00222157 组成；配对健康收益约 -0.00006904，净收益约 0.23785232。数值见 [26_e3_formal_experiment_report.md](26_e3_formal_experiment_report.md) 第 5 节。

**DERIVED。** Set 的正收益主要来自真实污染抵消，而非健康场景额外改善；但 Hard 和 Soft 的攻击 MSE 收益更大（分别约 0.24280207、0.24536527）。因此当前 No-Go 与“Set 有恢复作用”并不矛盾：它否定的是相对强基线的预注册优势。

## 7. 直接竞争文献核查边界

这里继承已有公式级审计，不重复声称本轮重新取得/阅读了全文。具体页码和公式见 [01_scope_and_competitors.md](01_scope_and_competitors.md) 和 [05_quickdet_palmdkf_fulltext_audit.md](05_quickdet_palmdkf_fulltext_audit.md)。

| 文献 | 已核查的相关模型/结果 | 对 B0 中心命题的关系 | 状态 |
|---|---|---|---|
| Deghat et al., Automatica 2019, DOI 10.1016/j.automatica.2018.10.052 | 误差/攻击跟踪、修正输出式 (30)、Thm. 3 和输出切换建议；见 01_scope 第 3 节 | 覆盖攻击跟踪和恢复思路；现有审计未发现跨历史事件的影响等价类 Oracle regret 下界。但不能仅因系统模型不同宣布新颖 | FACT：已有出版社公式审计；非本轮重读 |
| Tabatabaei et al., Automatica 2025, DOI 10.1016/j.automatica.2025.112460 | 状态/输出/攻击重构式 (12)—(18)，以及安全控制和边界；见 01_scope 第 3 节 | 具有模型约束的攻击重构与恢复；目前项目审计没有对其全部定理作“可辨识下界”专项排重 | FACT：已有出版社公式审计；针对 B 的差距为 OPEN |
| Gupta et al., Signal Processing 2026, DOI 10.1016/j.sigpro.2026.110516 | 条件 KF 式 (5)—(8)、起点混合式 (15)—(16)、多策略后验式 (19)—(22)；见 01_scope 第 3 节及 05 | 处理多种起点/策略解释和历史相关创新；事件后验/软估计是强竞争基线。已有报告称未见缓存 Replay 的目标影响不可辨识 minimax 下界，但不能将“未见”当作完整领域证明 | FACT：已有正文精读；S1/S2 补充证明未独立核查 |
| Mao et al., Control Engineering Practice 2026, DOI 10.1016/j.conengprac.2026.107102 | 局部后验均值和协方差式 (39)—(43)，包括模式间分歧及 CI；见 05 第 3 节 | 已覆盖多模式概率融合；模式是当拍链路噪声/DoS 状态，不是历史 Replay 索引。未在既有核查中发现目标影响不可恢复下界 | FACT：已有正文精读；B0 针对性下界审查仍 OPEN |

**OPEN。** 此外，用户指定的 Functional Observability/Functional State Estimation、Unknown Input Reconstruction、Undetectable Attacks、Switched-System Identifiability、Set-Membership/Minimax Recovery、Delayed/Out-of-Sequence Measurements 六类尚未完成逐篇选文、全文和定理核对。G1 旧材料已明示功能可辨识、GLS、传播、Schur 等属于标准工具，例如 [g1_retroactive_recovery/04_theorem_candidates.md](../g1_retroactive_recovery/04_theorem_candidates.md) 的 T3。没有证据支持“跨事件核空间包含关系本身是新定理”。本轮不能给出“未被任何现有论文覆盖”的终局新颖性结论。

## 8. 可陈述的中心命题及证明

### 命题：条件目标误差集合半径给出共同补偿器 Oracle-regret 下界

**DERIVED / STANDARD。** 固定合法在线信息 (z)，设所有与 (z) 相容的假设 (i\in\mathcal I(z)) 下，目标真实误差条件分布具有有限二阶矩，条件均值为 (m_i(z))，协方差为 (V_i(z))。在线补偿器只可选择一个共同动作 (u(z))。则：

1. 对每个解释 (i)，条件平方损失为
   \[
   R_i(u\mid z)=\operatorname{tr}V_i(z)+\|m_i(z)-u\|^2.
   \]
2. 相对已知解释的条件平方损失 Oracle，
   \[
   \inf_u\sup_{i\in\mathcal I(z)}[R_i(u\mid z)-R_i(m_i\mid z)]
   =\inf_u\sup_i\|m_i(z)-u\|^2,
   \]
   即条件均值集合 (M(z)=\{m_i(z)\}) 的最小包围球半径平方。
3. 因为任意集合的最小包围球半径至少是直径的一半，
   \[
   \inf_u\sup_i\mathcal G_i(u\mid z)
   \ge \tfrac14\operatorname{diam}(M(z))^2.
   \tag{7}
   \]

**证明。** 对条件分布 (e_i\mid z,i)，写 (e_i=m_i+(e_i-m_i))。交叉项条件均值为零，故 (E\|e_i-u\|^2=\operatorname{tr}V_i+\|m_i-u\|^2)。Oracle 选择 (u=m_i)，风险为 (\operatorname{tr}V_i)，相减得到平方距离。最小化解释集合上最大平方距离即为最小包围球半径平方；任意球半径至少为集合直径一半，故得 (7)。证毕。

**适用假设和限制。** 该命题需要：给定 (z) 后的解释集合/条件分布明确定义；比较的是同一在线信息下不同解释所要求的动作；若用 Bayes 风险还需指定解释先验；覆盖失败或模型外事件必须有有限损失/尾部矩控制。它是标准条件均值投影与 minimax 几何结论，不包含 Replay 特定结构，因此单独不足以满足本任务 Go 判据。

**Replay 结构带来的可能增量仍未建立。** 若要变成 G1-R 特定结果，需进一步证明：(M(z)) 如何由缓存传播矩阵、年龄、(O_h,G_h) 和联合交叉协方差构造；其半径/下界何时随通信间隔或缓存年龄变化；并与现有 E3 的 `ZERO_OR_UNRESOLVED`、动作率和风险排序建立非平凡联系。当前没有该定理。

## 9. 方向可行性 Go/No-Go

| 负责人门槛 | 本轮判断 | 依据 |
|---|---|---|
| 1. 跨事件模型与真实代码一致 | **部分通过** | (z=\eta+O_h\theta,\Delta=G_h\theta) 与已存 12 维窗口、24 个 O/G 矩阵一致；但合法有界参数域未被完整定义 |
| 2. 超出普通单模型秩/核条件的实质结果 | **未通过** | 跨事件核条件是标准线性代数；现有 84 对堆叠 O 均满列秩，未出现非平凡跨事件结构零空间；E3 年龄/性能差异不能由该核结构解释 |
| 3. 真实风险或 Oracle regret 下界 | **部分通过但属标准** | 可推导 (7)，使用条件误差均值集合；尚未将其化为 Replay 特定非平凡定量界或覆盖失败下无条件界 |
| 4. 未被直接竞争文献完整覆盖 | **未定** | 四篇直接论文已有审计，但六类文献专题核查不全；不能宣称新颖性已确认 |
| 5. 解释 E3 至少一个稳定差异 | **探索性相关、尚不足** | 24 汇总单元的动作率与 σ_min(O) 相关约 0.87，但非独立、混杂严重；缺逐 Seed 集合几何配对分析 |
| 6. 不依赖大规模仿真/更改估计器 | **理论起步可满足** | 矩阵与结果可做只读分析；但若需确认因果/推广，未来或需新设计，当前不授权 |

**本轮结论：B0 不通过进入算法/实验开发；理论方向资格目前为 NO-GO / STOP-PENDING-REVIEW。** 更准确地说，已提出的“跨事件核条件 + 两点三角不等式”不足以成为独立创新；标准 regret 半径命题可作为分析工具，但未体现缓存 Replay 特定的新理论增量。由于专题文献审查不完整，这不是“证明整个可恢复性问题无意义”，而是“按当前明确门槛，现有资产尚无资格立项为独立论文方向”。

## 10. 仍缺证据与停止条件

### 10.1 本轮未完成或数据不支持的分析

**OPEN。**

- 完整合法参数可行域及其对跨事件相容性的限制；
- 直接从实际缓存/接收日志定义每个 Seed 的在线 (z)-条件影响集合，并计算其直径、中心和零点关系；
- 将该集合几何与每个 Seed 的 E3 动作、损失逐行配对。E3 汇总文件不足以单独生成这些统计；Run 原始 JSON 存在，但这需要新增只读解析分析，不是本轮已有证据；
- 对六类专题文献逐篇核查不超过 10 篇直接相关论文的模型/定理/公式；
- 对保存矩阵做任意精度秩证明以及跨年龄受限参数域的精确交集分析；
- 目标影响等价类与正常风险预算 (U) 的端到端有限样本定理。

任务要求允许继续从已有 Run 读取做确定性只读分析，但本轮停止结论已由更关键问题决定：结构核条件没有非平凡跨事件冲突，已有公式等价条件是标准结果。上述缺口不应被写成已完成，也不应在没有负责人审核前转为下一轮任务。

### 10.2 若负责人要求再审，必须先满足的停止门槛

只有当后续文献和矩阵审查能同时给出以下证据，才值得重新考虑 B：

1. 找到一个不是普通 (\ker O\subseteq\ker G) 的 Replay/缓存特定定理，例如由缓存更新、间歇日程和相关历史参数共同决定的可恢复性阈值或不可恢复下界；
2. 定理的对象与合法在线创新窗口严格一致，所有参数—噪声—健康误差交叉协方差均纳入；
3. 下界是目标真实 MSE 或明确的 Oracle regret，而不是只给污染拟合残差；
4. 能解释至少一个已观测的 E3 年龄/事件现象，并在 Seed 配对数据上有可检验量；
5. 直接文献排重完成，且方法增量不能由标准功能可观测性、GLS、条件 Gaussian 估计或一般集合 minimax 直接给出。

任一条件失败，则封存 B，不转向 C，不为通过门槛降低要求。

## 11. 总结

**FACT。** G1-R 已证明/验证固定场景中的传播递推、共同协方差建模、E2 覆盖、E3 真实 MSE 及 `NO_GO_PERFORMANCE`。旧 G1 工作已包含单事件功能可辨识核条件；跨阶段固定坐标审计还没有发现“单阶段不够、联合阶段才出现新可辨识方向”的特例，见 [02_matrix_results.md](../cross_phase_identifiability_audit/02_matrix_results.md) 和 [04_gate_decision.md](../cross_phase_identifiability_audit/04_gate_decision.md)。

**DERIVED。** 本轮将单事件条件推广写成跨事件块核条件，且证明事件不可辨与影响可辨在逻辑上可分；给出污染残差和真实 Oracle regret 的标准两点/集合下界。对当前保存的 G1-R 矩阵，24 个单事件响应满列秩，所有同年龄跨事件块响应满列秩；未发现可支持独立创新的非平凡结构不可辨识例子。统计候选分布有不同协方差，故结构接近不等于分布相同。

**结论。** 当前核心命题主要由标准功能可辨识、Gaussian 条件矩和 minimax 集合半径组成。还没有得到超出这些标准结果、与 Replay 缓存/间歇日程有关、能解释 E3 的新定理；因此按冻结 Go 判据 **B0 不建议进入下一阶段**。这不是对 Replay 恢复问题无意义的判断，也不是数据质量否定。六类专题文献排重尚缺，故新颖性是未确认，而非已证明不存在。

本报告到此停止。没有修改算法、协议、Yang 仿真核心或旧结果；没有消耗 Seed、生成随机轨迹、运行 E2/E3、提交 Git 或 Push。
