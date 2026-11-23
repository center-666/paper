# N01执行｜同一实际记录上的数值误差与似然坐标

## 一、输入、状态及参照对象

本轮采用阶段十验收方案中的V2系统和原固定攻击族。令 \(Y_t\) 为实际发送后接收载荷，\(c_t\) 为传感器与接收端共同使用的实际中心。数学接收记录为 \((c_t,\gamma_t,Y_t\mathbf1_{\{\gamma_t=1\}})\)。本拍先揭示中心，再产生事件，发送后形成接收载荷，最后进行接收更新。实际monitor是该合法历史的因果函数。[验收合同](../paper2_stage10_acceptance_20261123/acceptance_checklist.md)

| 对象 | 定义 | 原型字段或处理 |
| --- | --- | --- |
| 实数nominal monitor \(m_t^-,m_t^+\) | 对同一实际载荷与中心执行精确Kalman更新的参照 | `MonitorFrame.nominal_prior`与`nominal_posterior`的外包 |
| 实际monitor \(\widehat m_t^-,\widehat m_t^+\) | 接收程序预测和更新后的binary64位模式 | `actual_prior`、`actual_posterior` |
| 真参数候选均值 \(\mu_{k,b,t}^\pm\) | 给定实际记录与候选参数的条件均值 | 独立精确有理数滤波用于确定性核对 |
| monitor数值误差 \(\xi_t^\pm\) | \(\widehat m_t^\pm-m_t^\pm\) | `prior_error`、`posterior_error` |
| nominal污染 | \(m_t^+-\mu_{k,b,t}^+=bH_{k,t}^+\) | 现有响应缓存的数学目标 |
| 实际monitor污染 | \(\widehat m_t^+-\mu_{k,b,t}^+=\xi_t^++bH_{k,t}^+\) | 有效输出风险使用的目标 |
| 精确输入值 | 已声明的Fraction、Decimal、整数或十进制文本 | `exact_value` |
| binary64输入值 | 某个已表示浮点数的精确二进制有理数 | `binary64_value` |

`Fraction("0.1")`与`Fraction.from_float(0.1)`具有各自精确的值。原型要求调用者显式指定语义，状态位模式统一用后者解释。似然选择零点使用精确载荷与中心之差。[数值原型](numerical_record.py)

### 1.1 连续模型与输入表示条件

数学推导允许连续真实输入。实际数值实现需要说明所读数值与数学输入之间的对应关系。确定性原型采用“所给有限十进制观测是声明的精确实数”合同，并对该合同下的后续运算误差作包围。对连续测量转换后的输入区间，需要补充其包含依据，再将区间传入核与零点包络。有限比特采集的概率质量模型属于相应通信模型的验证内容。

已有性能生成器使用binary64高斯采样和误差坐标，归档主要保存指标、种子与查询记录。它在似然入口使用`repr(float(...))`作为十进制文本。本轮区分其显示文本值与底层binary64精确值，确定性检查分别验证两种表示。N06重放需要固定输入解释并补充逐拍输入及monitor状态日志。[阶段九生成器](../paper2_stage9_cumulative_evidence_20261123/paired_recovery.py)

### 1.2 输入转换的可计算区间

若已知一个真实输入经IEEE binary64最近偶数舍入得到 \(z\)，则相邻浮点值的中点给出闭舍入单元 \(\mathcal J(z)\)。闭端点处理可保守包含ties。正、负最大有限值采用其外侧虚拟相邻值的中点，正、负零采用最小subnormal的半间隔。`binary64_rounding_cell`以精确二进制有理数实现该包含条件。

对已给输入区间 \(Y_t\in\mathcal Y_t\)、\(c_t\in\mathcal C_t\)，式(2)的更新残差包围可写为
\[
\mathcal E_t^{\rm upd}
=\widehat m_t^+-T_t\widehat m_t^--K_t\mathcal Z_t,
\quad
\mathcal Z_t=\mathcal Y_t\ \text{或}\ \mathcal C_t.
\]
将其代入式(3)，再用式(7)计算nominal坐标的输入区间，即得到完整的输入到误差、核和风险的包含链。主定理的条件历史继续采用精确连续记录，代码区间用于包围该记录中的数值。使用舍入单元时，真实转换实现满足最近偶数舍入是需核对的输入合同。原型当前的似然入口已实现精确输入分支，区间输入及移动零点带仍按N03推进。

## 二、monitor误差的精确恒等式

Riccati状态与增益按模型参数的精确有理数定义，记
\[
K_t=P_t^-C^\top(CP_t^-C^\top+R_{\gamma_t})^{-1},\qquad
T_t=I-K_tC,
\]
\[
R_1=R,\quad R_0=R+Z^{-1},\qquad
z_t=\begin{cases}Y_t,&\gamma_t=1,\\c_t,&\gamma_t=0.\end{cases}
\]
精确参照monitor更新为
\[
m_t^-=Am_{t-1}^+,\qquad m_t^+=T_tm_t^-+K_tz_t.
\tag{1}
\]
初始先验单独按给定值定义。实际程序可以采用浮点矩阵乘法、创新式更新及其实际运算顺序。对已记录的状态位模式，定义局部残差
\[
e_t^{\rm pred}=\widehat m_t^--A\widehat m_{t-1}^+,
\quad
e_t^{\rm upd}=\widehat m_t^+-(T_t\widehat m_t^-+K_tz_t).
\tag{2}
\]
式(2)右侧的浮点状态和已声明输入均作为精确有理数运算，因此局部残差可精确计算。实际增益转换、输入转换、创新计算和加法的影响通过实际最终状态进入更新残差。由相减得到
\[
\xi_t^-=A\xi_{t-1}^++e_t^{\rm pred},\qquad
\xi_t^+=T_t\xi_t^-+e_t^{\rm upd}.
\tag{3}
\]
初始误差由 \(\widehat m_0^--m_0^-\) 给定。以外向区间传播式(3)，归纳即得 \(\xi_t^\pm\in\Xi_t^\pm\)，进一步有
\[
m_t^\pm\in\widehat m_t^\pm-\Xi_t^\pm.
\tag{4}
\]
该方法主要传播数值误差，局部残差用实际位模式精确求值。其成本、包围宽度和有限数处理随实现记录。[`MonitorEnclosure`](numerical_record.py)

## 三、候选响应与数值误差的连接

对每个固定起点、幅值候选，真实量测在发送时为 \(Y_t-b\mathbf1_{\{t\ge k\}}\)。其后验与精确nominal参照使用同一中心、同一事件协方差和同一增益。相减得
\[
H_{k,t}^+=T_tAH_{k,t-1}^+
+\gamma_tK_t\mathbf1_{\{t\ge k\}},\qquad
m_t^+-\mu_{k,b,t}^+=bH_{k,t}^+.
\tag{5}
\]
因此
\[
\widehat m_t^+-\mu_{k,b,t}^+=\xi_t^++bH_{k,t}^+.
\tag{6}
\]
式(5)的响应取决于可信事件和协方差。原型复用阶段六的外向响应计算，对各 \(H_{k,t}^+\) 作包围。确定性检查还从载荷和候选幅值直接运行独立有理数滤波，验证式(5)、(6)及响应包含。[既有响应与物理核](../paper2_stage6_vector_correction_20261122/01_vector_kernel_and_pollution.md)

## 四、将同一记录换到nominal创新坐标

定义相对于实际monitor的精确实数创新与中心残差
\[
\widehat u_t=Y_t-C\widehat m_t^-,\qquad
\widehat r_t=c_t-C\widehat m_t^-.
\]
这些是精确差值的定义。软件中实际执行的浮点减法若产生另一个数值，其误差也需要包围。相对于精确nominal参照，令
\[
u_t=Y_t-Cm_t^-=\widehat u_t+C\xi_t^-,\qquad
r_t=c_t-Cm_t^-=\widehat r_t+C\xi_t^-.
\tag{7}
\]
当前发送候选幅值为 \(b_t=b\mathbf1_{\{t\ge k\}}\)，先验响应为 \(H_{k,t}^-=AH_{k,t-1}^+\)。以实际monitor为中心的候选偏移为
\[
d_{k,b,t}=-C\xi_t^--bCH_{k,t}^-.
\tag{8}
\]
令 \(S_t=CP_t^-C^\top+R\)、\(V_t=S_t+Z^{-1}\)。代入实际坐标的联合核，有
\[
\widehat u_t-b_t-d_{k,b,t}=u_t-b_t+bCH_{k,t}^-,
\]
\[
d_{k,b,t}-\widehat r_t=-bCH_{k,t}^--r_t,
\qquad
\widehat u_t-b_t-\widehat r_t=Y_t-c_t-b_t.
\tag{9}
\]
因此可在nominal坐标复用原来的物理候选核。健康候选在实际monitor坐标中的均值偏移为 \(-C\xi_t^-\)。在nominal坐标，健康均值偏移为零。两者是同一概率模型在给定过去后的已知平移，载荷变换的Jacobian为一。

这一平移在事件/载荷前已经由过去数值误差决定。似然仍条件于本拍已揭示的可信中心，中心生成机制在所有参数解释下共同。量化中心的合法性在其实际生成坐标核查，nominal中心残差允许带有 \(C\xi_t^-\) 的偏移。[实际坐标联合核](../paper2_stage3_joint_detection_20261121/01_joint_observation_theory.md)

## 五、保持移动零点和强凹似然结构

记 \(\eta_{k,i}=CH_{k,i}^-\)、\(v_i=Y_i-c_i\)。对固定起点的精确对数似然比仍有
\[
\ell_{k,t}(b)=\mathsf A_{k,t}b-\tfrac12\mathsf B_{k,t}b^2
+\sum_{i=k,\gamma_i=1}^t
\{\log h(v_i-b)-\log h(v_i)\},
\tag{10}
\]
\[
\mathsf A_{k,t}=\sum_{\gamma_i=1}\frac{(1-\eta_{k,i})u_i}{S_i}
-\sum_{\gamma_i=0}\frac{r_i\eta_{k,i}}{V_i},\qquad
\mathsf B_{k,t}=\sum_{\gamma_i=1}\frac{(1-\eta_{k,i})^2}{S_i}
+\sum_{\gamma_i=0}\frac{\eta_{k,i}^2}{V_i}.
\]
各和从 \(k\) 至 \(t\)。式(7)的误差包围进入 \(u_i,r_i\) 的区间。选择项使用原始载荷与中心之差，其共同平移精确抵消。精确有限十进制输入下，移动零点可继续精确保存。一般输入区间需要另对 \(Y_i-c_i\) 及可能的零点位置作外包。

在零点之外，对每个固定的真实输入实现，旧强凹曲率依然成立。上界计算中，中点函数值与导数取可靠区间，曲率取统一下界，因而切线上界可同时覆盖输入与响应的区间不确定性。原型复用`VectorRecord.likelihood`和`tangent_upper`，仅在输入和缓存构造处传入修正区间。[强凹上界](../paper2_stage5_certification_acceleration_20261122/01_piecewise_strong_concavity.md) · [缓存适配](numerical_record.py)

### 5.1 参考过程与证书目标

warm参考状态仍由事件历史预先递推，每拍用nominal坐标下的归一化核评分。代码`core.ref`围住的是 \(\mathsf E_t=q_t/p_{0,t}\)，其中 \(p_{0,t}\) 为该nominal参照下的健康历史密度。相应候选缓存围住 \(\Lambda_{k,b,t}=p_{k,b,t}/p_{0,t}\)。在该共同基准下，可靠删除条件为
\[
\overline\Lambda_{k,I,t}<\varepsilon\underline{\mathsf E}_t.
\tag{10a}
\]
这个比较通过同一精确健康密度的代数抵消，等价于候选密度与参考密度的原条件。式(7)的区间输入分别包住这些比率的真实值，参考下端与候选上端共同控制安全排除。未来把这些包围接入累计外包时，仍按式(10a)执行。

现有方向搜索的对象为nominal污染 \(bH\)。针对实际monitor的风险证书另把 \(\Xi_t^+\) 接入式(6)的污染外包。新原型提供相应的有效动作风险计算，完整来源签发和累计外包集成按N03–N06继续验证。[覆盖与外包合同](../paper2_stage10_acceptance_20261123/acceptance_checklist.md)

## 六、有效输出的风险下界

对已发布binary64状态 \(\widehat m_t^r\)，精确有效动作为
\[
\widehat a_t=\widehat m_t^+-\widehat m_t^r.
\]
令 \(\mathcal S_t\) 为已具有覆盖依据的参数外包，\(\mathcal H_{k,t}\) 为响应外包。则覆盖事件上真实的实际monitor污染属于
\[
\widehat\Theta_t\supseteq
\{\xi+bH:(k,b)\in\mathcal S_t,\xi\in\Xi_t^+,H\in\mathcal H_{k,t}\}.
\tag{11}
\]
计算 \(\underline s_t\le\inf_{\theta\in\widehat\Theta_t}\theta^\top W\widehat a_t\)，则
\[
\Delta\widehat R_t\ge2\underline s_t-\widehat a_t^\top W\widehat a_t.
\tag{12}
\]
原型`effective_risk_lower`按原始状态位模式取得有效动作，将误差盒和响应盒映射为实际污染盒，再用外向支撑下界与精确二次型计算式(12)。其调用者提供参数区间的覆盖依据。确定性输出夹具给定参数区间，以独立精确污染核对不等式，夹具结果属于算术验证。

## 七、本轮确定性证据与范围

检查覆盖全部32种五拍事件串、长静默、大状态小更新及接收创新流夹具，共35种确定性历史。参照monitor、候选均值与污染响应使用独立Fraction递推。似然数值诊断直接计算物理核的100位Decimal对数倍率，并与区间缓存交叉核对。另验证了零密度未决后的状态完整性、最小subnormal的输入表示及联合核数值归一化。[检查结果](numerical_contract_checks.json)

大状态压力例的初始状态含 \(10^{16}\) 尺度分量。其一拍中 \(C\xi_t^-=-0.13872\)，实际中心残差为0.002，而nominal中心残差为−0.13672。该确定性例展示需要保留的坐标平移项。其数值属于所设压力输入。对典型攻击轨迹的实际影响和计算成本按N06另行记录。

当前原型的选择零点要求载荷与中心之差有精确有限十进制表示。连续输入转换区间、可能零点带的处理、完整证书来源和累计外包集成，以及24条历史轨迹的再认证均列在执行状态中。全时域统计覆盖的闭合需要把这些条件接入同一合法记录和同一参考过程。
# 追加记录：实际量化中心与区间输入

`NumericalLikelihoodRecord.append` 在任何状态提交之前检查 `abs(c-C m̂⁻) ≤ δq`，这里的预测向量取已记录的 binary64 位模式并按精确有理数解释，中心按声明的精确输入解释。等号接受，越界拒绝。此检查只验证中心处于规定半宽度内，不能独立证明中心来自指定相位量化器、来源绑定或完整的时序合法性。独立的 `MonitorEnclosure` 用于审计给定状态记录，其接口本身不验证量化中心。

对于可能的中心区间 `[c₋,c₊]` 与预测量测区间 `[p₋,p₊]`，残差包含在 `[c₋−p₊,c₊−p₋]`。整个外包落在 `[-δq,δq]` 才判为合法，整个外包与该集合不相交才判为非法，其余返回未决。区间相依性忽略会增加未决数，不会使该外包判断误判合法。

发送选择项使用 `v=Y−c`、候选幅值区间 `B`，分别包围 `log h(v−B)` 和 `log h(v)`。候选零点可能出现时，前者下端点取负无穷。健康分母可能为零或数值下界无法排除零时返回未决。该运算给出指定连续输入点态似然比的外包，不能直接解释为舍入记录的概率质量或整体历史置信过程。原型尚未接入累计似然、参考混合和历史证书，亦未建立区间输入下的全时域覆盖。
