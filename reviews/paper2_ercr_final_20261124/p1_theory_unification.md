# P1 理论统一：可信历史约束下的向量污染集合与条件风险校正

## 研究范围与记号

本稿按 2026-11-24 的研究决策冻结模型为单节点集中式远程估计，采用二维状态、一个标量传感器和一个可信发送/静默位。攻击在触发位生成后修改已发送载荷，攻击起点未知，幅值 b 属于 [0,b_max] 恒定并持续。攻击不改变触发位、共享预测中心或历史记录。暂不纳入攻击停止时刻、变幅攻击、有限字长上行码字和多估计节点。

系统为

    x_(t+1) = A x_t + w_t,   y_t = C x_t + v_t,

其中 x_t 属于 R^n，y_t 属于 R，噪声独立高斯，初始分布为高斯。论文示例使用 V2 参数，但以下结论依赖线性高斯结构、单标量量测和触发核。

时刻 t 的可信中心为 c_t。它必须在事件生成前由双方可见的过去信息和共享随机数确定。定义 r_t=c_t-C m_(t)^M,-，S_t=C P_t^- C^T+R，V_t=S_t+Z^-1。m_(t)^M,-、P_t^- 是攻击无感知 Monitor 的先验。触发机制为

    P(gamma_t=1 | y_t,c_t) = g(y_t-c_t),
    g(q) = 1-exp(-Z q^2/2).

先生成 gamma，再作攻击。接收载荷为

    z_t = y_t + gamma_t b 1{t >= k},

其中 k 是未知固定起点。静默时不产生载荷。概率模型把量测和连续载荷视为实数。现有仿真将 binary64 数值转换为十进制文本后作为精确连续输入送入似然计算，这不等价于真实浮点码字的离散概率模型。

记 F_(t-1) 为事件生成前接收端可用的历史、可信中心及已公开共享随机数所生成的过滤族。所有候选和参考核均条件于同一条历史及同一个 c_t。

## 引理 1：事件条件下的高斯协方差闭合

对候选 theta=(k,b)，接收历史给定后的状态条件分布仍为高斯，且候选条件协方差与 Monitor 协方差相同。其更新仅依赖 gamma_t：

    R_1=R, R_0=R+Z^-1,
    K_(gamma,t)=P_t^- C^T (C P_t^- C^T+R_gamma)^-1,
    P_t^+=(I-K_(gamma,t)C)P_t^-,
    P_(t+1)^-=A P_t^+ A^T+Q.

**证明。** 若 gamma_t=1，候选知道干净量测 y_t=z_t-b 1{t>=k}。给定这个量测后，触发因子 g(y_t-c_t) 是已知常数，在状态后验归一化时抵消，故为标准 Kalman 更新，噪声方差为 R。若 gamma_t=0，接收端没有量测，但事件概率为 exp[-Z(Cx_t+v_t-c_t)^2/2]。将其对高斯 v_t 积分，得到关于 x_t 的高斯似然，其等价量测为 c_t，等价噪声方差 R+Z^-1。该更新协方差不依赖候选均值或中心残差。因此每个候选与 Monitor 在同一事件历史下共享协方差递推。□

该引理依赖中心 c_t 已知且预测可测。若中心是接收端未知的隐藏相位索引，或事件由攻击后载荷触发，Stage 6、9 的闭合推导不直接适用。

## 定理 1：固定幅值攻击的向量污染响应

令 m_(t)^(theta,-), m_(t)^(theta,+) 为正确候选 theta=(k,b) 下的条件均值，m_(t)^(M,-), m_(t)^(M,+) 为 Monitor 均值。定义

    delta_t^- = m_(t)^(M,-)-m_(t)^(theta,-),
    delta_t^+ = m_(t)^(M,+)-m_(t)^(theta,+).

则

    delta_t^+ = (I-K_(gamma,t)C) delta_t^- + gamma_t K_(1,t)b 1{t>=k},
    delta_(t+1)^- = A delta_t^+.

定义零初值响应 H_(k,t)^+ 属于 R^n：

    H_(k,t)^+ = (I-K_(gamma,t)C) A H_(k,t-1)^+
                + gamma_t K_(1,t) 1{t>=k},
    H_(k,-1)^+ = 0.

则每个合法观测历史上有精确恒等式

    delta_t^+ = b H_(k,t)^+.

**证明。** 设 T_(gamma,t)=I-K_(gamma,t)C。发送时，Monitor 用 z_t-Cm_t^(M,-) 更新，正确候选用 y_t-Cm_t^(theta,-) 更新。两者创新之差为 b 1{t>=k}-C delta_t^-。相减得到 delta_t^+=T_(1,t)delta_t^-+K_(1,t)b1{t>=k}。静默时两者使用相同可信中心，故 delta_t^+=T_(0,t)delta_t^-。预测步给出 delta_(t+1)^-=A delta_t^+。对该式作归纳，得到响应递推及 delta=bH。证明没有使用 H 的分量非负性，H 可以有正负分量。□

该递推与 Stage 6 `VectorRecord` 的响应相同。Stage 6 还给出了有限窗口污染 b[H_t(k_0)-H_t(k_1)]，但本稿固定为持续攻击，不把有限窗口结果混入主实验。

## 定理 2：连续发送/静默记录的条件似然

定义发送残差 u_t=z_t-Cm_t^(M,-)，中心残差 r_t=c_t-Cm_t^(M,-)，候选先验均值偏移 d_t^(theta)=-C delta_t^-，攻击注入 a_t=b1{t>=k}。相对于静默原子和发送载荷 Lebesgue 测度，条件观测核为

    p_theta(0 | F_(t-1)) = (1+Z S_t)^(-1/2)
                            exp(-(d_t^(theta)-r_t)^2/(2V_t)),

    p_theta(1,u | F_(t-1)) = phi_(S_t)(u-a_t-d_t^(theta))
                              g(u-a_t-r_t),

其中 phi_S 为方差 S 的零均值高斯密度。这是一条归一化联合观测核。

**证明。** 在候选模型下，干净量测创新 e_t=y_t-Cm_t^(M,-) 服从 N(d_t^(theta),S_t)。发送后 u_t=e_t+a_t，发送概率为 g(e_t-r_t)，变量代换即得发送次密度。静默概率是

    integral phi_(S_t)(e-d_t^(theta)) [1-g(e-r_t)] de,

高斯乘积完成平方后得到上式。两种观测质量相加等于

    integral phi_(S_t)(e-d_t^(theta)) {g(e-r_t)+1-g(e-r_t)} de = 1.

这也说明当前事件按干净量测生成、攻击只修改已经发送的载荷，是该似然的必要时序假设。□

相对于健康核，单拍似然比为

    ell_(theta,t)(0) = exp((2 r_t d_t^(theta)-(d_t^(theta))^2)/(2V_t)),

    ell_(theta,t)(1,u) = exp((u(a_t+d_t^(theta))-(a_t+d_t^(theta))^2/2)/S_t)
                        * g(u-a_t-r_t)/g(u-r_t).

完整历史似然比 L_t^theta=product_(i=0)^t ell_(theta,i)(O_i)，L_(-1)=1。

固定起点 k 下，高斯项关于 b 为二次式，发送选择项有移动零点 u_i-r_i-b=0。连续幅值认证必须切分移动零点并使用区间上界。有限幅值网格只能作探索性诊断。

## 定理 3：参考似然过程与全时域候选覆盖

令 P_0 为健康观测模型。取有限参考幅值 beta_j 属于 [0,b_max]，固定权重 lambda_j>=0 且 sum_j lambda_j=1。每个 j 指定一个由当前历史可预测、在静默原子和连续发送载荷上归一化的参考条件观测核 q_(j,t)。定义

    ell_(j,t) = q_(j,t)(O_t | F_(t-1)) / p_(0,t)(O_t | F_(t-1)),
    w_t = 1/((t+1)(t+2)),     a_t = 1/(t+2),
    M_(j,-1)=0,
    M_(j,t) = (M_(j,t-1)+w_t) ell_(j,t),
    R_t = a_t + sum_j lambda_j M_(j,t).

约定 a_(-1)=1，则 a_(t-1)-a_t=w_t。于是 R_t 非负、R_(-1)=1，且在健康模型下

    E_0[R_t | F_(t-1)] = R_(t-1).

对任意固定真实候选 theta，定义

    C_t^epsilon = {vartheta : L_t^vartheta >= epsilon R_t},
    0 < epsilon < 1.

若候选和参考核在每个有限时域对 P_0 互相绝对连续，则

    P_theta{ theta belongs to C_t^epsilon for all t>=0 } >= 1-epsilon.

**证明。** 每个参考核归一化，所以 E_0[ell_(j,t)|F_(t-1)]=1。递推给出 E_0[M_(j,t)|F_(t-1)]=M_(j,t-1)+w_t。再由 sum_j lambda_j=1 和 a_(t-1)-a_t=w_t，得到式 (10)。因此 R_t 是 P_0 下的非负均值一似然过程，Q_t=R_t P_(0,t) 构成一致的有限时域概率测度。由于 L_t^theta=P_(theta,t)/P_(0,t)，R_t/L_t^theta=dQ_t/dP_(theta,t) 是 P_theta 下的非负均值一似然比鞅。Ville 不等式给出

    P_theta{sup_t R_t/L_t^theta > 1/epsilon} <= epsilon.

置信集外意味着 L_t^theta < epsilon R_t，属于上述越界事件，由此得证。共同支持由式 4 的正静默概率、式 5 在发送载荷上几乎处处为正，以及 a_t>0 保留的健康参考质量保证。□

这是对每个固定真实参数分别成立的全时域覆盖，不是把不同真实参数放在同一概率测度下的同时覆盖。所有数据依赖方向都使用同一个参数覆盖事件，无需按方向数作 Bonferroni 分配。

### Stage 9 参考递推核对

Stage 9 `VectorRecord.append` 采用 beta_j 属于 {0.05,0.10,0.25}、lambda_j=1/3，代码索引 n=t，`weight = 1/((n+1)(n+2))`，并用 `ref = sum(mass)/3 + 1/(n+2)`。这与上述 R_t 索引一致。每个 reference 当前偏移由过去记录递推，故其核可预测。证明所需条件是核归一化和递推质量守恒，不要求把 R_t 解释为实际物理攻击起点的先验混合。

数值上，参数盒 B 只有在

    upper(L_t(B)) < epsilon * lower(R_t)

时才可整体删除。Stage 9 的向外区间对数似然上界、参考下界和严格不等式剪枝符合这一规则。区间跨阈值、移动零点未分段、节点预算耗尽或输入无法按观测合同解释时，必须保留候选并返回未决。

## 推论 1：候选覆盖诱导污染外包覆盖

定义时刻 t 的候选污染像

    D_t = {b H_(k,t)^+ : (k,b) belongs to C_t^epsilon}.

若在线程序生成 Dhat_t superset D_t，并且只用经认证的似然不等式或方向约束删除参数，则在定理 3 的覆盖事件上，真实污染 delta_t^+ 属于 Dhat_t 对所有 t 成立。

**证明。** 覆盖事件上真实参数属于每个 C_t^epsilon。似然剪枝仅排除低于同一置信门槛的参数。方向证书仅排除与已证明支撑约束不相容的候选。定理 1 给出真实污染为 bH_(k,t)^+，遂有结论。□

Stage 9 在首张正方向证书之后，为每个攻击起点维护一个或多个闭幅值区间，并使用似然增量上界收缩。方向证书应用时根据响应系数的可靠上端 q^+ 向下外包幅值下界 b>=z/q^+。这构成覆盖意义下的参数外包，但不是完整置信集的显式枚举，也不自动给出紧的向量污染凸包。Stage 6 的凸包几何原型以已给定端点为输入，性能试验没有端到端执行全向量投影。

## 定理 4：污染集合上的最坏条件风险与凸投影

给定可信历史，正确候选下 x_t 的条件分布为 N(mu_t^theta,P_t)，Monitor 均值为 m_t^M=mu_t^theta+delta_t^theta。对任意历史可测动作 a_t，发布估计 m_t^R=m_t^M-a_t，且不回写 Monitor。则条件加权均方风险差为

    R_t^M - R_t^R = 2 (delta_t^theta)^T W a_t - a_t^T W a_t.

设 D_t 是非空有界真实污染集合，K_t=cl conv(D_t) 是其闭凸包。则

    max_a inf_(delta in D_t) {2 delta^T W a - a^T W a}
      = dist_W(0,K_t)^2,

且最优动作为 p_t=argmin_(p in K_t) p^T W p。严格正的共同安全动作存在，当且仅当 0 不属于 K_t。

**证明。** 条件均值正交性给

    R_t^M = tr(WP_t)+||delta_t^theta||_W^2,
    R_t^R = tr(WP_t)+||delta_t^theta-a_t||_W^2,

相减得风险恒等式。令 p_t 为原点到 K_t 的 W-范数投影。投影最优性给 (delta-p_t)^T W p_t >=0，因此 a=p_t 时风险改善至少 ||p_t||_W^2。对任意 a，由 p_t 属于 K_t 得

    inf_(delta in D_t) (2 delta^T W a - ||a||_W^2)
      <= 2 p_t^T W a - ||a||_W^2
      = ||p_t||_W^2 - ||a-p_t||_W^2.

故 p_t 达到极小极大值。若 0 属于 K_t，对任意非零 a，原点是其凸组合下的候选污染，最坏改善至多 -||a||_W^2；零动作取得零。若 0 不属于 K_t，则投影 p_t 非零并给出严格正改善。□

若使用保守污染外包 Dhat_t superset D_t，则在 Khat_t=cl conv(Dhat_t) 上投影仍能保护真实候选，只会更保守。损伤上界

    B_t = sup_(delta in Dhat_t) delta^T W delta

描述外包污染能量，不等价于正风险改善证书。若 Dhat_t 是按起点分组的若干幅值闭区间的像，每个像 H_(k,t)[l,u] 是线段，其凸包可由所有线段端点构造，凸二次能量最大值也可在端点求得。认证端点必须向外舍入。

## 推论 2：可计算方向证书

选定非零方向 d_t。若连续参数验证器证明

    inf_(delta in Dhat_t) d_t^T W delta >= z_t > 0,

则动作

    a_t = eta_t [z_t/(d_t^T W d_t)] d_t,   0<=eta_t<=1,

在外包上有条件风险改善下界

    (2 eta_t - eta_t^2) z_t^2/(d_t^T W d_t).

未能证明正支撑、搜索未决或数值复核失败时取零动作。这是 Stage 9 当前单方向动作的保证形式。它是凸投影极小极大解的可计算保守实现，不能表述为实际程序已经在每拍求得完整 p_t。

若实际 binary64 相减产生动作 ahat=a+xi，且 |delta_j|<=rho_j，则

    2 delta^T W ahat - ahat^T W ahat
      >= 2 z_t [d_t^T W a/(d_t^T W d_t)]
         - 2 sum_j rho_j |(W xi)_j| - ahat^T W ahat.

Stage 9 用精确二进制有理数审计此下界，并在下界为负或动作超限时回退为零。此输出审计连接了理论动作和实际状态减法，但似然仍采用连续输入合同，不代表完成了浮点舍入单元或有限字长信道概率认证。

## 失效概率和总体期望风险

定理 4 与方向证书只在真实污染属于认证外包集合的事件上给条件风险保证，不保证每条实际状态轨迹的平方误差下降。若另有全路径界 ||delta_t||_W<=B_theta、||a_t||_W<=B_a，且全时域覆盖失败概率不超过 epsilon，则可得

    E sum_(t<T) (R_t^M-R_t^R)
      >= E sum_(t<T) ||a_t||_W^2
         - 2 epsilon T (B_theta B_a + B_a^2).

Stage 6 向量失效预算与此形式一致。V2 小样本的最坏污染包络较大，该通用失效惩罚很保守，目前不支持无条件总体 MSE 收益主张。论文主保证宜限定在条件风险和覆盖事件上，实际累计损失另作经验指标。

## 实现与结论的对应关系

| 结论 | 当前审查 | 可用表述 |
|---|---|---|
| 条件协方差递推 | Stage 6 高斯核推导成立，要求中心可预测、事件先于攻击 | 给定可信事件历史时，候选与 Monitor 共享事件条件协方差递推 |
| 向量污染响应 H b | Stage 6 递推、代码与确定性有理数检查一致 | 固定事件记录下，条件均值污染线性依赖未知恒定幅值 |
| 全时域候选覆盖 | Stage 9 参考过程和 Ville 推导成立于连续载荷联合核 | 每个固定真实候选以至少 1-epsilon 概率在所有时刻留在置信集合 |
| 连续幅值外包 | Stage 9 已实现首张方向证书后的按起点多区间外包 | 已实现来源绑定的连续幅值方向证书原型，不声称显式枚举完整置信集 |
| 全向量凸投影 | Stage 6 有给定端点的精确几何原型，Stage 9 性能流程未端到端执行全投影 | 给出极小极大投影定理并实现可计算方向证书 |
| 条件风险不增 | 真实污染属于可信外包时成立 | 覆盖事件上的条件风险改善，不写无条件攻击检测或逐轨迹保证 |
| 数值可信性 | 输出动作有精确有理数审计，似然输入仍按连续十进制实数解释 | 不声称完成有限字长通信概率模型 |
| 性能 | Stage 6 小样本、强攻击收益区间跨零；Stage 9 查询仍为秒级 | 不声称显著总体 MSE 改善或实时运行 |
| 攻击实验 | Stage 6/9 为未知起点、恒定非负幅值持续攻击；TRSR Oracle 有有限窗口组 | Oracle 只作独立潜力和延迟边界，不合并至主模型效果统计 |

## 建议的论文第 3、4 章

### 第 3 章 可信通信记录下的攻击历史与向量污染

1. 事件时序、可信中心和连续载荷合同。
2. 发送/静默联合观测核及条件高斯更新。
3. 固定起点、恒定非负幅值攻击的向量污染递推。
4. 参考似然过程、时间一致候选集合和连续参数外包。
5. 来源绑定和历史证书更新。

### 第 4 章 污染集合上的最坏条件风险校正

1. 条件风险差恒等式。
2. 污染凸包投影极小极大定理。
3. 原点分离的可恢复性判据。
4. 连续参数方向支撑证书和动作限幅。
5. 实际输出数值审计及安全回退。
6. 覆盖失效预算和适用边界。

本稿完成 Stage 6、Stage 9 的内部数学统一，但不能替代公式级直接近邻全文审查。完整凸包端到端实现、确认性独立实验和创新性裁决仍待完成。

## 仓库依据

- 系统参数：`reviews/paper2_stage6_vector_correction_20261122/model.json`
- 条件观测核和污染响应：`reviews/paper2_stage6_vector_correction_20261122/01_vector_kernel_and_pollution.md`
- 风险投影及向量失效预算：`reviews/paper2_stage6_vector_correction_20261122/03_projection_and_directional_certificate.md`
- 方向证书幅值信息：`reviews/paper2_stage6_vector_correction_20261122/08_certificate_transport_information_loss.md`
- 累计置信外包证明：`reviews/paper2_stage9_cumulative_evidence_20261123/01_theory.md`
- 增量外包和来源绑定：`reviews/paper2_stage9_cumulative_evidence_20261123/cumulative_envelope.py`
- 逐拍实现和攻击时序：`reviews/paper2_stage9_cumulative_evidence_20261123/paired_recovery.py`
- Stage 6/9 实验边界：`reviews/paper2_stage6_vector_correction_20261122/07_pilot_results.md` 与 `reviews/paper2_stage9_cumulative_evidence_20261123/02_results.md`
