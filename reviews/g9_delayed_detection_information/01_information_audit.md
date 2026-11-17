# G9：后续量测独立检测信息审查

日期：2026-11-16。范围：最后一次有限数学筛选；不运行仿真、不生成随机轨迹、不开发检测器、不改变研究方向。

**结论建议：NO-GO。理论问题可以严格定义，已有主模型也确有后续条件新增信息，工程核验成本很小；但本轮结果仍由标准条件Gaussian、Schur信息分解和线性响应秩解释，未通过“超出普通GLRT和线性可检测性”的硬门槛。**

不能将此结论改写为“后续量测没有用”。本轮确认的正面事实是：在明确的完整到达信息基线下，主事件第一拍后的本地量测即提供非零条件信息，16拍的指定方向信息增量约6.38%。这个数不是检出率改善，也不构成算法创新。

标签：**FACT**＝已有代码/报告/矩阵支持；**DERIVED**＝本轮明确假设下的推导或确定性复算；**HYPOTHESIS**＝未验证；**OPEN**＝证据不足。立项与停止由研究负责人最终审核。

## 1. 继承、基线与本轮实际操作

**FACT。** 隔离分支g1r-e2-status-contract-20261115，HEAD为788204a388155c9604348fc09d6ce510691c3fc4。本轮开始时G8报告为未跟踪文件，保留原状。本轮只新增本报告；不提交、不推送。

主要来源：

- [G8成果收束报告](../g8_g1_paper_closure/01_paper_decision_audit.md)：单包48/48报警没有分离到达分歧与后续信息；持续FDI/恢复结果不能替代单包检测增量。
- [G7-R0](../g7_sod_conditioned_retrospective_detection/01_core_problem_audit.md)：继承NO-GO及统计边界，不重新包装SoD选择或条件阈值。
- [G1原统计审计](../fdi_replay_20261112/identifiability_audit.md)：共享缓存误差、相关残差和信息饱和。
- [G1-R传播验收](../g1_retroactive_recovery/07_full_horizon_propagation_audit.md)、[P0纯响应与接口](../g1_retroactive_recovery/code/p0_verified.py)：原Yang不变，单次注入的全网/缓存响应已验证。
- [跨阶段审计03号](../cross_phase_identifiability_audit/03_identifiability_and_statistics.md)，特别是T4—T7：相关信息分解与同信息强基线已经写过。
- [跨阶段矩阵结果](../cross_phase_identifiability_audit/02_matrix_results.md)：保存响应、协方差、正面信息增益和原No-Go。
- [G1-R联合统计07号](../g1r_risk_constrained_recovery/07_replay_joint_probability_model.md)、[既有纯矩阵系数函数](../g1r_risk_constrained_recovery/code/replay_joint_statistics.py)：只对Gaussian原始噪声建立线性系数，不抽样。
- [G6-R0文献矩阵](../g6_retrospective_detection/01_research_direction_audit.md)：继承反向检测、lifted攻击可辨识及有限后续窗口的既有竞争。

**FACT。** 本轮计算只有：

1. 读取旧NPZ，检查最早本地innovation响应；
2. 从旧协方差取子块，计算压缩到达残差与后续缓存残差的条件信息；
3. 复用healthy_raw_coordinates和healthy_error_coordinates两个现有纯矩阵函数，构造完整合法到达历史及后续原始本地量测的联合矩；
4. 两坐标核验和线性代数复算。

没有调用simulate、generate_data、随机数、旧runner的main；没有生成新Run、拟合检测器、重新校准或重新计算实验p值。新增量是数学审查，不是新性能试验。

## 2. 必须首先解决的语义问题：量测、创新与历史参照

### 2.1 物理量测并未被本攻击改变

**FACT，simulation/model.py和engine.py。**
\[
x_{t+1}=Ax_t+w_t,\qquad y_i(t)=H_ix_t+v_i(t),
\tag{1}
\]
物理状态没有来自滤波估计的控制反馈。本次链路FDI只改某次接收载荷：
\[
q^a_{ji}(\tau)=\hat x_j(\tau)+\delta.
\tag{2}
\]
它改变估计与缓存，不改变x或本地传感器y。

**DERIVED，命题A。** 在固定绝对时刻、相同物理初态/噪声先验下，若检测器只获得
\[
Y_L=\operatorname{col}(y_i(\tau+1),\ldots,y_i(\tau+L))
\]
而没有任何与被攻击包有关的历史参照，则
\[
P_\delta(Y_L)=P_0(Y_L)
\tag{3}
\]
对所有L成立。任何仅依赖Y_L的检验，在该简单假设下有\(P_D=P_{FA}\)。

证明：按相同原始物理噪声耦合，式(1)的x和y在两假设下逐项相等。其推前分布相同。本结论不需要Gaussian；但不适用于另有执行器/物理反馈攻击的模型。若按数据选择随机攻击时刻再条件化，也必须另处理时间选择，不能直接套固定τ的表述。

**重要区别。** 式(3)不意味着\(P_\delta(Y_L\mid\mathcal I_0)=P_0(Y_L\mid\mathcal I_0)\)。正常情况下新量测与历史真实包相关；受攻情况下，同一个可见包值可能对应不同的真实状态条件分布。后续量测可以核查这种跨时间一致性。

### 2.2 “不使用到达分歧”有两种不同含义

1. **不在到达时用分歧分数报警，但保留合法收到的包作为未来验证参照。** 这允许研究条件新增信息，问题成立。
2. **完全禁止使用到达包及任何包含其影响的估计记忆，只给后续原始y。** 则命题A适用，无检测能力。

若\(\mathcal I_0\)已经包含q、自己的估计和当前量测，到达空间残差或缓存分歧是它们的确定函数。禁止显式计算一个分数，不等于从信息集中删除相同证据。两方比较须先冻结信息集，不能以隐藏一个变量名称制造“独立新信息”。

### 2.3 后续innovation不是后续原始量测的同义词

\[
\nu_i(t)=y_i(t)-H_i\hat x_i(t).
\tag{4}
\]
\(\hat x_i(t)\)包含历史受攻包和之后收到的邻居包。若L超过某些新邻居到达时刻，innovation的输入信息不止Y_L，还包括这些新包。

本轮分别使用：

- **纯后续量测信息：** \(\sigma(\mathcal I_0,Y_L)\)，不增加τ后的邻居消息；
- **后续innovation特征：** 允许实际滤波历史的函数，但必须如实登记其含有的后续消息信息。

在τ+1时，\(\hat x_i(\tau+1)\)已由τ时合法信息确定；所以给定完整\(\mathcal I_0\)，\(\nu_i(\tau+1)\)与\(y_i(\tau+1)\)只是已知平移。此时非零innovation响应本身不能被当成另一份独立物理证据。

## 3. 公平比较的信息集和概率模型

### 3.1 本轮明确采用的完整到达基线

**DERIVED / 建模定义。** 为避免弱化到达基线，令
\[
\mathcal I_0=
\sigma\{y_i(0{:}\tau),\ (e,t,q_e(t))_{\text{实际入边接收},\,t\le\tau},
\text{公开模型、固定发送日程}\}.
\tag{5}
\]
原Yang自己的状态、创新、缓存、发送历史均可由这些记录和已知初始化重构，不另计为独立信息。这里不包含真状态、原始未篡改攻击包、攻击标签或未发送邻居状态。

后续只增加Y_L。所有到达先验、攻击候选、噪声假设及虚警预算两方相同。不使用实际运行的未来健康反事实；下面的健康系数和协方差是离线公共模型计算。

**本轮数值范围：** 原五节点异质模型、公共gap8、节点1、边0→1、τ=200、固定未知FDI向量δ。把攻击位置/时刻固定是此次可行性审查的明确先验，不代表已解决未知事件扫描。

### 3.2 Gaussian位置族的适用条件

假设δ是确定向量，不随当前/未来噪声选取；τ与日程外生固定；Yang线性更新、没有cap/隔离反馈。用有限维合法记录Z_0表示\(\mathcal I_0\)，选定后续特征Z_L，则
\[
\begin{bmatrix}Z_0\\Z_L\end{bmatrix}
\sim N\left(
\begin{bmatrix}\mu_0\\\mu_L\end{bmatrix}
+
\begin{bmatrix}A_0\\A_L\end{bmatrix}\delta,\ 
\begin{bmatrix}
\Sigma_{00}&\Sigma_{0L}\\
\Sigma_{L0}&\Sigma_{LL}
\end{bmatrix}\right).
\tag{6}
\]
保留所有跨时交叉协方差。冗余确定坐标先去除；正定情形如下，退化情形需在共同支持子空间上计算。

对纯原始后续量测\(Z_L=Y_L\)，**\(A_L=0\)**。到达记录中的目标包有\(A_0\)的单位块，其他既往记录无攻击均值偏移。

随机Replay参数、自适应选择FDI或真实SoD不自动满足(6)。G7/G1-R已有的非Gaussian选择、参数—创新相关性边界全部继承；本轮不扩展为它们的通用结论。

## 4. 理论门槛：后续量测究竟增加什么信息

### 4.1 一般分布下的精确条件KL分解

**DERIVED / STANDARD。** 对固定简单备择δ，在相关分布绝对连续且KL有限时：
\[
D(P_\delta^{Z_0,Z_L}\|P_0^{Z_0,Z_L})
=
D(P_\delta^{Z_0}\|P_0^{Z_0})
+
E_{P_\delta^{Z_0}}
D(P_\delta^{Z_L\mid Z_0}\|P_0^{Z_L\mid Z_0}).
\tag{7}
\]
证明由联合密度分解\(p(z_0,z_L)=p(z_0)p(z_L\mid z_0)\)，对数似然相加后取期望。

右侧第二项才是相对于到达信息的新增检测信息。它为零，当且仅当两条件律在相应意义下几乎处处相同。它不是“新增量测的边际KL”，也不等于某个检测器的实际功效增量。复合假设需要固定相同的参数集合/先验，不可事后对不同方法选不同最有利参数。

### 4.2 条件Gaussian分解与完整证明

令
\[
K=\Sigma_{L0}\Sigma_{00}^{-1},\quad
S=\Sigma_{LL}-\Sigma_{L0}\Sigma_{00}^{-1}\Sigma_{0L},
\quad \widetilde A_L=A_L-KA_0.
\tag{8}
\]
定义仅用于理论分析的正常条件预测误差：
\[
W_L=Z_L-\mu_L-K(Z_0-\mu_0).
\tag{9}
\]
则
\[
W_L\mid\delta\sim N(\widetilde A_L\delta,S),
\quad \operatorname{Cov}(W_L,Z_0)=0.
\tag{10}
\]
在固定δ的共同Gaussian族内，零交叉协方差给独立性；对随机δ边际混合不能照搬该独立性。

**证明。** 由(6)直接求均值和协方差得到(10)。变换\((Z_0,Z_L)\mapsto(Z_0,W_L)\)可逆，联合Gaussian成为两个独立块，故
\[
J_{0:L}=J_0+\Delta J_L,\quad
J_0=A_0^T\Sigma_{00}^{-1}A_0,\quad
\Delta J_L=\widetilde A_L^TS^{-1}\widetilde A_L\succeq0.
\tag{11}
\]
条件新增KL为
\[
\Delta D_L(\delta)=\tfrac12\delta^T\Delta J_L\delta.
\tag{12}
\]
这也是(7)在共同协方差位置族下的结果。

**关键判据。**
\[
\text{给定方向δ有新增信息}\iff \widetilde A_L\delta\ne0;
\quad
\text{所有非零方向均有新增信息}\iff
\operatorname{rank}\widetilde A_L=n_\delta.
\tag{13}
\]
不能用\(\operatorname{rank}A_L\)或未来残差幅值代替(13)。

### 4.3 原始未来量测没有攻击均值，仍可有条件信息

纯Y_L的\(A_L=0\)，于是
\[
\widetilde A_L=-\Sigma_{Y0}\Sigma_{00}^{-1}A_0.
\tag{14}
\]
因此新增证据来自：后续量测对到达包中正常状态/估计误差成分的预测关系。若该预测关系在攻击方向为零，则无新增信息；若非零，即使后续y的边际分布完全不变，仍能提供一致性证据。

这不是假设攻击影响物理系统，也不是把后续量测当作独立噪声样本。

### 4.4 估计传播造成的“信号”须扣除已知历史的确定部分

若某个未来innovation满足
\[
Z_L=Y_L-BZ_0
\]
（例如τ+1时对完整到达信息而言），则
\[
A_L=-BA_0,\quad
\Sigma_{L0}=\Sigma_{Y0}-B\Sigma_{00},
\]
代入(8)后
\[
\widetilde A_L=-\Sigma_{Y0}\Sigma_{00}^{-1}A_0.
\tag{15}
\]
确定的受污染估计平移B完全消去。故“攻击在innovation中传播得更大”不自动等于新增统计信息更大；必须相对于已有记录条件化。多拍若依赖τ后的邻居消息，应把这些消息另列，不能继续只写\(Y_L-BZ_0\)。

### 4.5 最小解析例子

**DERIVED / STANDARD。** 令
\(q=x+e+\delta\)、\(Y_\ell=x+v_\ell\)，其中x、e及各v独立N(0,1)。这是信息分解例子，不是重新设定Yang实验。

仅看全部Y，H0/H1同分布；但给定q，
\[
E_\delta[Y_L\mid q]=\tfrac12(q-\delta)\mathbf1,\quad
\operatorname{Cov}(Y_L\mid q)=I+\tfrac12\mathbf1\mathbf1^T.
\]
因此
\[
J_0=\tfrac12,\qquad
\Delta J_L=\frac{L}{2(L+2)},\qquad
J_{0:L}=\frac{L+1}{L+2}\longrightarrow1.
\tag{16}
\]
第一条未来量测就增加1/6信息，但无限增加量测仍受单个历史估计误差e限制。该例说明条件证据与信息饱和，不是新检测器或新系统定理。

## 5. “最少多少拍”必须分成三个问题

### 5.1 最早出现未条件化innovation响应

**FACT / DERIVED。** 攻击在τ接收后，
\[
\Delta\hat x_i(\tau)=0,\quad
\Delta\hat x_i(\tau+1)=\epsilon A\delta,
\quad
\Delta\nu_i(\tau+1)=-H_i\epsilon A\delta.
\tag{17}
\]
原P0响应矩阵已验证这一时序。在当前主模型
\[
-H_1\epsilon A=
\begin{bmatrix}
-.012&-.0012\\0&-.0808
\end{bmatrix},
\tag{18}
\]
奇异值约0.0808091113、0.0119986470，秩2。对既有δ=[1.2,−.8]，首拍响应为[−.01344,.06464]。

因此**不使用到达分歧的本地innovation，从τ+1起即有非零边际响应；所有非零δ都不被该首拍矩阵消掉。** 这只是结构响应时间，不是保证已检测。它也不证明该信号独立于I0；独立新增量须用(13)。

### 5.2 最早出现相对于I0的条件新增信息

定义
\[
L_{\rm info}(\delta)=\min\{L\ge1:\delta^T\Delta J_L\delta>0\}.
\tag{19}
\]
全部方向的对应条件是\(\operatorname{rank}\Delta J_L=n_\delta\)。第6节完整信息计算在所保存双精度模型和交叉核验精度下，L=1即为满秩，所以该数值实例的\(L_{\rm info}=1\)。这不是所有系统/链路的结论，也不是一个已完成符号证明的普遍最小延迟定理。

若\(\widetilde A_L\delta=0\)对全部允许L成立，则未来量测永远不能在该方向增加条件证据。检测能力是否已由I0提供是另一问题；“没有新增”不等于“联合完全不可检测”。

### 5.3 达到指定功效需要多少拍

仅有“矩阵非零/满秩”不能给出低误报高检出的最小整数。对固定已知方向和幅度δ、共同Gaussian简单假设、最优定长NP检验，
\[
P_D^{joint}(L)
=1-\Phi\!\left(z_{1-\alpha}
-\sqrt{\delta^T(J_0+\Delta J_L)\delta}\right).
\tag{20}
\]
只使用新增条件因子(9)而不使用到达似然分数时，把\(J_0+\Delta J_L\)换成\(\Delta J_L\)。若要求功效≥1−β：
\[
\sqrt{\delta^T(J_0+\Delta J_L)\delta}
\ge z_{1-\alpha}+z_{1-\beta}.
\tag{21}
\]
式(20)是理论最优简单假设结果，不是实际未知δ的GLRT表现。未知方向/未知事件需统一相同先验、扫描及阈值处理。多次查看也不能沿用单次α。

**OPEN。** 用户没有冻结目标β、最小攻击幅值、未知参数处理及查看时刻规则，所以不存在当前可诚实给出的统一“L拍必检”数值。任意小δ与无界Gaussian噪声下，不可能给所有非零攻击统一有限时域高功效保证。信息饱和时某些功效要求甚至永远达不到。

## 6. 现有Yang模型的只读矩阵核验

### 6.1 完整到达信息，后续只加本地原始量测

**DERIVED。** 复用原健康系数函数，构造截至τ=200的节点1全部本地量测及实际入边接收包，删除初始化恒为零的包坐标。无真值、标签或未发送估计进入待检信息集。

- 到达记录：251条二维记录，共502个标量；矩阵秩502；
- \(\Sigma_{00}\)最小特征值约0.00662598；
- 后续量测：节点1的201—216，最多16个二维时刻；
- 不加入τ后的邻居消息；这些时刻y可由既有系数恒等式ν+Hhat得到，矩阵中的估计项相消，仍是原始本地y；
- 全部模型参数取已有P0配置及07号NPZ，不改A/H/Q/R/K或发送日程。

到达设计信息：
\[
J_0\approx
\begin{bmatrix}
17.79927216&-20.87526581\\
-20.87526581&88.36710649
\end{bmatrix},
\quad
\delta^TJ_0\delta=122.26641043
\tag{22}
\]
其中δ=[1.2,−.8]只用于沿用旧FDI方向做数学展示，不输入在线规则。

| 后续本地量测数L | ΔJ最小特征值 | ΔJ最大特征值 | δ方向新增信息δᵀΔJδ | 相对J0方向信息增量 |
|---:|---:|---:|---:|---:|
| 1 | .07983734 | .57442555 | 1.04885904 | 0.857847% |
| 2 | .10351044 | 1.10736170 | 1.98181494 | 1.620899% |
| 3 | .11054156 | 1.59758383 | 2.82730159 | 2.312411% |
| 4 | .11267229 | 2.04285748 | 3.59117390 | 2.937171% |
| 7 | .11369189 | 3.10695355 | 5.41172598 | 4.426176% |
| 8 | .11374462 | 3.37699912 | 5.87337354 | 4.803751% |
| 16 | .11386368 | 4.50289896 | 7.79773310 | 6.377658% |

**范围。** 这些是已知候选、已知模型、固定FDI位置族的解析信息量，KL新增量为该方向新增信息的一半。不是检出率、不是百分比MSE收益，也不是已校准检测器。不能因6.38%“看起来像性能增益”就宣布论文门槛通过。

该I0保存了整个本地历史，强于旧短窗口评分；这样做是为了避免人为削弱基线。若另有限内存约束，必须事先给双方相同约束，不能为放大增量事后删减I0。

### 6.2 为什么弱到达特征会放大表观增量

仅读取旧跨阶段NPZ，令压缩基线仅为到达缓存残差\(R_0=y_i(\tau)-H_iq(\tau)\)，之后加同一归档包的\(R_1,\ldots,R_L\)，得到：

| L | 压缩基线方向信息 | 新增信息 | 合计 |
|---:|---:|---:|---:|
| 1 | 3.79090049 | 1.05248304 | 4.84338353 |
| 3 | 3.79090049 | 2.40693853 | 6.19783902 |
| 7 | 3.79090049 | 4.20677396 | 7.99767445 |

7拍新增/原压缩基线约111%，与完整I0下4.43%明显不同。两者都是各自明确信息集下的数学量，不能互相替代，也不能以较大百分比选论文主结果。条件新增量本身不必随基线信息扩充单调；比较必须基于统一基线和总信息。

本表只用来审计到达基线的定义，不作为允许直接使用到达分歧的新检测方案。完整I0审查也没有在τ实际发出告警。

### 6.3 独立坐标核验与计算成本

原始x/估计/raw-cache系数函数与已有误差/对齐缓存系数函数分别计算，最大绝对差：

| 量 | 差 |
|---|---:|
| innovation loading | 3.44×10^-15 |
| 各时刻hat loading | 2.85×10^-14 |
| e0 loading | 7.85×10^-15 |
| target x loading | 0 |

两坐标的J0方向信息差约2.7×10^-9，L=16新增信息差约2.1×10^-9；联合逆与Schur分解相对差约2.63×10^-11。表格只报告相应有效精度，不把双精度计算叫成有向舍入证明。

完整到达信息的首轮矩阵构造/计算约5.1秒；独立坐标核验为数秒量级。仅说明现有资产足以低成本进行数学核查，不是在线检测器时延或算法效率比较。新随机轨迹、Seed调用和阈值拟合均为0。

## 7. 证据何时消失，哪些攻击仍无法检测

**DERIVED。** 应区分三个对象：

1. **已收集历史信息。** 固定I0且不断添加Y时，累计\(\Delta J_L\)不减；已经记录的统计证据不会因为缓存覆盖而自动消失。
2. **新增一拍的条件信息。** 可能减小、为零或趋于零；若新块在已有信息条件下对攻击方向没有区分力，就不再增加信息。
3. **当前innovation的攻击响应。** 可因稳定传播而衰减，也可能暂时为零；缓存在q被替换不保证网络估计污染在q归零。旧传播报告已证明后续真新包也可能携带反馈污染。

对于本轮共同Gaussian位置族：

- 完整联合记录不可检测方向是\(\ker[A_0;A_L]\)；“相对于I0无新增”方向是\(\ker\widetilde A_L\)，不能混为一谈。
- 在只使用后续原始Y且不保留包参照的限制下，全部FDI方向均受命题A限制。
- 若使用后续innovation，未条件化的不可见方向由保存的响应O确定；条件新增仍须扣除与I0的预测关系。
- H_i的单拍秩、物理可观测秩和网络攻击响应秩是不同对象。不能只看H_iA^a就推出全部条件信息不可辨识，尤其到达记录本身有相关先验。
- “分布不同”不保证有限窗口高功效；小幅、弱方向及共享健康误差可使证据很弱。

本轮不新增拓扑、秩亏模型或攻击方向来寻找有利例子，也不以末尾时刻有限的矩阵表宣称渐近消失定理。

## 8. 创新门槛：是否超过普通GLRT和线性可检测性

**FACT。** 项目2026-11-14的跨阶段审计03号T6已经给出
\[
I_J=I_C+\widetilde O_P^TS^{-1}\widetilde O_P
\]
并明确称标准Schur条件信息累积。其02号已保存指定方向7.997674、0.061332、8.718084，以及联合相对缓存段约9.01%的信息增量。那些旧数字的基线是整个缓存阶段，不是本次I0，不能重复当G9新发现。

**DERIVED。** G9的新整理价值是把“原始未来y不受攻击”“给定历史包后却有条件证据”“innovation包含历史信息”和“最小结构/功效延迟”分清，并在完整合法I0下补了确定性数值。这解决表述和审计问题，但目前没有构成以下任一种实质理论增量：

- 超出标准Gaussian条件化的可计算性能保证；
- 由Yang缓存结构产生、不能直接用现有响应/秩/Schur解释的最小延迟定理；
- 在相同完整信息下超出标准最优检验/GLRT的能力；
- 一种已经验证的工程资源优势。

**既有竞争边界。** 不展开新文献调研，仅继承G6/G8已审内容：

- Zhang2022/2023的反向检测已用后续输出检验历史等效改变；
- Gupta的历史条件似然及未知起点处理不是纯即时检测；
- Sun–Cho–Hwang2025 *On attack detection and identification for the cyber–physical system using lifted system model*（Automatica，DOI10.1016/j.automatica.2025.112243）已有lifted响应、跨模式可辨及有限后续窗口条件，见G6第7节原文定位；
- G1现有full-prefix GLS正是同类Gaussian均值偏移下的标准工具。

没有据标题宣布文献完全覆盖所有G9细节，也没有把协议名称差异作为创新。**按负责人硬门槛，本轮创新门槛未通过。**

## 9. 三道硬门槛与停止决定

| 门槛 | 审查结果 |
|---|---|
| 理论：后续量测提供什么新增信息？ | **通过明确化。** 原始y边际无攻击信息，但相对合法历史的条件KL可增加；公式(7)—(15)给精确定义。当前完整主模型第一拍即有满秩条件增量。 |
| 创新：是否超出普通GLRT/线性可检测性？ | **未通过。** 当前证明均属标准链式KL、Gaussian正交化、Schur与线性响应；主模型一拍结构结果直接来自满秩H_iA。 |
| 工程：能否小代价验证？ | **矩阵级通过。** 已复用两套旧纯系数函数完成数秒级交叉核验；没有新传播器、轨迹或检测器。真正实测功效尚未验证，不能假装完成。 |

**总决定建议：NO-GO，停止本条历史量测检测路线的继续算法/实验扩展，提交负责人审核。**

依据是三道硬门槛中的创新门槛未过，**不是**因为条件新增信息为零，也不是因为原工程无效。本轮不推荐再次更换GLS、CUSUM、阈值、窗口或网络以寻求正面论文结果；不预先安排最小实验。

下一步唯一事项是研究负责人审核并确认本次最后理论筛选的结论。不会自动进入下一阶段。

## 附录A：完整I0数值的可复核方式

以下为本轮只读计算的核心步骤，使用已有函数；不另保存检测程序，不运行旧main。参数及来源均为冻结配置/矩阵。生成的是模型噪声系数，不是随机状态轨迹。

~~~python
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(
    "reviews/g1r_risk_constrained_recovery/code").resolve()))
from replay_joint_statistics import healthy_raw_coordinates

cfg = json.loads(Path(
    "reviews/g1_retroactive_recovery/results/"
    "g1r_p0_verified_20261113_v1/config.json"
).read_text(encoding="utf8"))["model"]

with np.load("reviews/g1r_risk_constrained_recovery/results/"
             "g1r_replay_joint_20261114_r01/replay_joint_matrices.npz",
             allow_pickle=False) as d:
    A, H, gains, schedule = [d[k].copy()
                            for k in ["A", "H", "gains", "schedule"]]

m = SimpleNamespace(
    cfg=cfg, A=A, H=H, gains=gains,
    Q=np.asarray(cfg["Q"]), P0=np.asarray(cfg["P0"]),
    R=np.asarray([r*np.eye(2) for r in cfg["R_variances"]]),
    edges=np.asarray(cfg["edges_sender_receiver"]),
    powers=np.stack([np.linalg.matrix_power(A, k)
                     for k in range(cfg["T"]+1)]))
r = healthy_raw_coordinates(m, schedule, 217, range(217), set(range(217)))
Y = np.stack([r["eta"][2*t:2*t+2] + H[1] @ r["hats"][t][1]
              for t in range(217)])

B0 = [Y[t] for t in range(201)]
O0 = [np.zeros((2, 2)) for _ in range(201)]
for e, (sender, receiver) in enumerate(m.edges):
    if receiver != 1:
        continue
    for t in range(201):
        q = r["hats"][t][sender]
        if schedule[t, sender] and np.max(np.abs(q)) > 0:
            B0.append(q)
            O0.append(np.eye(2) if (e, t) == (0, 200)
                      else np.zeros((2, 2)))

B0, O0 = np.concatenate(B0), np.concatenate(O0)
F = np.concatenate(Y[201:217])
C = np.linalg.cholesky(B0 @ B0.T)
W = np.linalg.solve(C, O0)
Z = np.linalg.solve(C, (F @ B0.T).T)
J0 = W.T @ W
S = F @ F.T - Z.T @ Z
T = -Z.T @ W
delta = np.array([1.2, -.8])

for L in [1, 2, 3, 4, 7, 8, 16]:
    dJ = T[:2*L].T @ np.linalg.solve(S[:2*L, :2*L], T[:2*L])
    print(L, np.linalg.eigvalsh(dJ), delta @ dJ @ delta)
~~~

独立复核时将healthy_raw_coordinates换为已有healthy_error_coordinates，其余观察坐标相同；不能在上述函数外调用生成轨迹或runner入口。对完整I0的矩阵增量分析没有拟合/校准环节。

## 附录B：关键来源哈希及保护

- 跨阶段主事件NPZ：
  reviews/cross_phase_identifiability_audit/results/c_phase_geometry_20261114_r01/full_gap8_main_e0_r200_d216.npz；
  SHA256 c761373179f4e3d5f74506a972bf788cc62e527ea540149b0f115f95d61e8f35。
- 07号联合NPZ：
  reviews/g1r_risk_constrained_recovery/results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz；
  SHA256 c02f7d0041fa568246d2788084fe2c78b9a5f912ab03166a0bb7830f3efa7c0a。
- 原始生成函数、Yang更新、G1/G1-R算法、E2/E3结果及G6/G7/G8报告不修改。保留G8未提交状态；本轮不commit、不push。

交付核验：274个受保护代码、配置、报告和既有矩阵文件SHA256前后相同；报告10个相对链接均存在。Git已跟踪文件和暂存区无差异，HEAD未变。本轮新增仅G9报告，原未跟踪G8目录保持原状。

