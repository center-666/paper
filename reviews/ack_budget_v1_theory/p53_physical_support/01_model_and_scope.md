# 01 模型、范围和执行时序

## 1. 原始资产及本轮继承

**FACT。** 从指定P5.2基准320744ea77e3f8637980d083e3365d255ac3bb79创建ack-v1-p5-3-physical-support-audit。原来位于ac2e935e的审查分支保持不动；本分支直接父基准为P5.2，不含其P6分析。本任务以新附件为准，不进入P6。

重新读取[旧稿](../../../papers/paper2_ack_budget_deadline/manuscript/paper.tex)，P5.2的[README](../p52_reachability/README.md)、[反例](../p52_reachability/02_counterexample.md)、[一般证明](../p52_reachability/03_reachable_states_and_proofs.md)、[成本规则](../p52_reachability/04_cost_neutral_rule.md)、[验证](../p52_reachability/05_validation_and_decision.md)、[通信自动机](../p52_reachability/code/reachability_audit.py)及[回归代码](../p52_reachability/code/test_reachability.py)。
本文采用旧原规则，不把成本中性规则用于物理见证。全部旧文件保持字节不变。

## 2. 固定物理系统

**FACT。** 旧稿eq:system、eq:parameters：
\[
x_{k+1}=Ax_k+w_k,\ y_{i,k}=H_ix_k+v_{i,k},\
A=\operatorname{diag}(51/50,101/100),\ Q=I_2/50,
\]
\[
H_1=H_3=H_5=[1,0],\ H_2=H_4=[0,1],\
R_i=1/5,\ x_0\sim N(0,I_2).
\]
独立初态、各时刻共同过程噪声w_k和所有节点/时刻量测噪声；不能把w_k复制成五份独立噪声。
每个节点量测为标量。Q≻0、R_i>0、P0=I≻0。

**FACT。** eq:yang保留
\[
\hat x_{i,k+1}
=A\hat x_{i,k}+K_i(y_{i,k}-H_i\hat x_{i,k})
+\sum_{j\ne i}C_{ji}(c_{ji,k}-\hat x_{i,k}),\
K_i=(3/5)H_i^\top,\ C_{ji}=(51/5000)A.
\]
全有向图20边，各边独立接收缓存和发送端同步副本。代码边按发送端、接收端排序，0号为1→2。节点下标在JSON的edges_one_based为1起始。

## 3. 初始化、时序及整数通信逻辑

**FACT。** eq:trigger、eq:cache、eq:deadline、eq:occupancy、eq:policy：

1. hat x_i,0=0、c_ji,0=0、τ_ji=0、失败历史空；k=0仅用y_i,0形成hat x_i,1。
2. k≥1预测c^-_ji,k=A c_ji,k−1，计算d^-_ji,k=hat x_j,k−c^-_ji,k。
3. γ=1{||d^-||²>θ²}，θ=1/5；等号属于低请求。
4. D=τ+B+1，u=|H∩[max(1,D−L+1),k−1]|，n=D−k+1。低请求不发送；高请求且n>B−u+1则等待，否则实际尝试。
5. 攻击者仅看到当前实际尝试，按各边过去有效阻断决定本拍阻断/放行，可靠及时ACK。
6. 成功c_ji,k=hat x_j,k，否则c_ji,k=c^-；低请求或成功令τ=k；失败追加时间戳。
7. 所有通信完成后才同时使用当前y_i,k形成hat x_i,k+1。

本任务最后时刻k=L记录全部20边触发及目标拍前状态，**尚不执行第L拍发送、阻断或新量测更新**。故最高用到y_i,L−1；没有偷用y_i,L或未来信息。

## 4. 概率空间与确定性中心

**DERIVED。** 足够的原始向量按时间排列为
\[
\zeta=(x_0,w_0,\ldots,w_{L-2},
v_{1,0},\ldots,v_{5,0},v_{1,1},\ldots,v_{5,L-1})\in\mathbb R^{7L}.
\]
这里过程部分2+2(L−1)=2L维，量测噪声5L维。协方差
\[
\Sigma_\zeta=\operatorname{diag}(I_2,(I_2/50)^{\oplus(L-1)},(1/5)I_{5L})
\]
严格正定，最小特征值1/50，密度处处>0。
本向量确实需要Q≻0来使其全部原始坐标非退化；若只考虑量测Y的全支撑，R_i>0已足够，不能把Q>0说成所有支持性证明的普遍必要条件。

构造中心取x0=0、全部w=0，则物理状态中心为0、y=v。它是支持空间中的一个点，其本身概率0；正概率来自03号文证明的完整7L维开球。开球允许x0、w和第二维量测全部变化，不将零坐标事件误说成正概率。

## 5. 本轮限制

**FACT。** 只作数学/确定性验证，参数B,L是分类定理的符号参数及任务指定有限核验，非修改历史实验配置。未运行旧引擎、MC、新正式Seed、误差性能比较或P6。
**OPEN。** 发生概率大小、长期频率、无限次到达及MSE/资源优势未处理；不宣称首次提出或论文创新性验收。
