# G1任务一：缓存episode统计模型与可辨识性审计

日期：2026-11-12。范围：只读核查现有五节点Yang-form代码、2026-11-11序贯缓存运行和用户设定；另给小模型解析。没有运行新状态轨迹。

## 1. 实际代码时序与统计接口

### 1.1 系统和增益

G1序贯验证实际取reference_exploration_plan中的heterogeneous_sensing模型：
\[
A=\begin{bmatrix}1&.1\\0&1.01\end{bmatrix},\quad Q=.02I,\quad
H_i\in\{\operatorname{diag}(1,.15),\operatorname{diag}(.15,1),\ldots\},\quad R_i=.05I.
\]
部分节点本地动态观测Gramian秩2，部分秩1，不能笼统称所有节点局部不可观。

model.nominal_gains按全边每步通信（q=1）联合误差协方差递推算增益：
\[
B=(I-\epsilon L)\otimes A,\quad
K_i=(BP)_{ii}H_i^T(H_iP_{ii}H_i^T+R_i)^{-1}.
\]
运行SoD、ZOH cache、检测器隔离和攻击时继续复用这组名义gain。故原Yang增益最优性/均方稳定定理不自动适用于G1闭环。代码明确把它称为nominal gain。

### 1.2 发送、缓存和接收时间

工程触发规则在engine中读取t开始前estimate；若没有外生schedule，则按
\[
send_j(t)=1\{\|\hat x_j(t)-m_j^{last}\|^2>\delta_{send}\}
\ \lor\ 1\{t-t_j^{last}\ge T_{\max}\}.
\]
t=0另行强制发送。本地量测y_i(t)每tick都由系统生成；在t形成发送决定后，才对该真实fresh estimate包做FDI/Replay。攻击不改变该tick的trigger决定。

接收端每条有向边分别保存最新真正收到的payload和last_receive time。接收年龄a下用于融合的缓存是\(A^a\tilde m_j(r)\)。monitor观察receiver自己的当前本地measurement、edge fresh标志、age、aligned cache及local estimate；不观察真值、未来或sender未发数据。

在下一个fresh包到达前，monitor残差每tick计算。**episode起点**是一个真实fresh package在该边到达的r（年龄0也产生一次残差）；**终点**是下一个fresh到达之前的时刻；若两次到达间隔为Δ，episode数据是r到r+Δ−1共Δ项。下一个fresh tick先flush旧episode，再用新缓存形成新episode的age 0分数。仿真末尾无下一个fresh的episode被标记right-censored；旧统计的训练/校准/FPR分母排除不完整episode。

原序贯主验证的gap8和irregular是外生重复发送日程，为保证方法之间机会一致；它们不是send-on-delta闭环SoD。SoD由原run_study/engine提供，但Episode GLS试验尚未在该真实closed-loop schedule验证。

### 1.3 噪声和估计误差的交叉相关

令发送时sender estimation error为\(e_j(r)=x_r-\hat x_j(r)\)，当前篡改量为b_r，定义cache error合成量\(q_r=e_j(r)-b_r\)。以下状态方程恒等式精确成立：
\[
r_a=y_i(r+a)-H_iA^a(\hat x_j(r)+b_r)
=H_iA^a q_r+\sum_{s=0}^{a-1}H_iA^{a-1-s}w_{r+s}+v_i(r+a). \tag{1}
\]

接收本地测量噪声与仅由过去sender历史形成的e_j在**未再条件化未来事件**时按原独立噪声假设独立；但e_j与物理状态x_r相关，未来measurement的状态部分也与e_j相关，正由q_r项的P_q处理。未来w/v彼此独立，然而不同年龄的r_a仍因共享q_r和跨时间过程噪声相关。若检测量改用receiver自己的滤波innovation，还另有receiver error与sender error的cross-covariance；当前缓存监视器使用的是measurement减对齐cache，未直接使用local_hat形成该残差。

## 2. 联合残差模型：精确式与条件式

**PROVED（代数恒等式）**：式(1)对每条轨迹成立，不需要Gaussian。

**CONDITIONAL（高斯联合式）**：如果条件于包抵达和攻击动作的历史后，q_r为\(N(m_q,P_q)\)，与之后w/v独立，且不条件于后续“本episode未结束”，那么
\[
E[r_a]=H_iA^am_q,
\]
\[
\operatorname{Cov}(r_a,r_c)=H_iA^aP_q(A^c)^TH_i^T+
\sum_{s=0}^{\min(a,c)-1}H_iA^{a-1-s}Q(A^{c-1-s})^TH_i^T+
1_{\{a=c\}}R_i. \tag{2}
\]

共享cache误差形成第一项跨年龄相关；共同过程路径形成第二项；各tick本地measurement noises只在对角块出现。

**实际触发选择使Gaussian不是自动成立。** Send-on-Delta事件条件化sender estimate是否越过阈值，通常是对Gaussian历史做截断。一个episode活到年龄a，还意味着之前每一tick都没有形成新包；这些no-send事件依赖sender estimate、共同state与过程噪声。按实际episode长度条件化后q_r及残差vector一般为截断/混合分布。因此式(2)不能被称作“真实协议下精确条件Gaussian”。

G1既有实现使用age-only发送规则生成train/cal residual episode，再经验估计每个phase/edge/prefix的联合均值和covariance；它是协议特定经验模型，不是解析正确条件协方差证明，也不自动迁移至改变cache/trigger规则的防御闭环。阶段、prefix长度和右删失口径需随应用完整报告。

## 3. \(A=H=1,Q=0,z_a=e-b+v_a\)：信息饱和和可辨识性

令episode内cache error e固定共享，v_a独立同分布。

### 3.1 cache error已知为零均值随机效应

若跨episode已知\(e\sim N(0,\sigma_e^2)\)，\(v_a\sim N(0,\sigma_v^2)\)，对固定攻击b：
\[
\mathbf z|b\sim N(-b\mathbf1,\Sigma_L),\quad
\Sigma_L=\sigma_e^2\mathbf1\mathbf1^T+\sigma_v^2I.
\]
估计b的Fisher information是
\[
I_L=\mathbf1^T\Sigma_L^{-1}\mathbf1=
\frac{L}{\sigma_v^2+L\sigma_e^2}\longrightarrow \frac1{\sigma_e^2}.
\]
prefix mean variance为\(\sigma_e^2+\sigma_v^2/L\to\sigma_e^2\)。随着本地测量增加，measurement noise平均消失，但不消除共享cache uncertainty；单episode关于固定b的信息饱和。只有\(\sigma_e=0\)时信息才按L线性增加。

代码中的toy结果：\(\sigma_e^2=1,\sigma_v^2=.2,b=.3\)，L=1,2,8,32,1000时prefix variance为1.2,1.1,1.025,1.00625,1.0002；见evidence/mechanism_checks_v3/covariance_floor.json。这是指定随机效应模型的精确数值，不是五节点拟合结果。

### 3.2 e未知时攻击偏置不可辨识

如果每个episode的e是任意未知常数，观测只依赖合成截距\(e-b\)。对任意b'令\(e'=e+b'-b\)，所有z_a逐项完全相等。因此**单episode不能分别辨识e和b**，只能估计合成偏移。

若e为跨episode独立抽样且其distribution/zero mean已知，固定b可通过大量独立episodes总体识别；但单个episode的Fisher information仍有上界。若e的均值/分布本身未知，则把e分布平移、把b反向平移给出相同观测分布，攻击偏置仍不可辨识。Send-on-Delta又会选择sender history与episode survival，真实e条件分布不保证为已知零均值Gaussian。

## 4. 触发及数据口径核查

- 本地measurement每tick取得；receiver monitor读真实y_i(t)、fresh/age/aligned cache。
- 实际SoD trigger在数据update前由pre-measurement sender estimate与last sent estimate决定；触发后才换payload。
- episode残差 age 0在fresh tick同刻计算。旧episode被下个fresh packet结束，残差只到fresh tick前一刻。
- 仿真终点的未完episode被右删失；原train/cal/tune/test完整episode误隔离率均以完整episodes为分母。
- sequential比较用fixed external gap8或irregular schedule，并非原Send-on-Delta闭环；SoD下候选统计分布尚未测。
- 现有名义gain按q=1全通信联合协方差设计，事件/缓存安全实验复用它。任何Yang原文的最优性、稳定结论不自动继承。
- attack packet只在send机会替换。Replay-packet按历史第8个实际send选来源；replay-matched由当前tick减80步且检查来源时刻也确有send。它在重复40步日程相位相同，匹配历史与当前发送间隔；不是一般任意历史内容选择。
