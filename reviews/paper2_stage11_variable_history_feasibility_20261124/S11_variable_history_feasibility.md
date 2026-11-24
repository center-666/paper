# S11 变量攻击历史与置信风险融合：竞争核查和数学可行性审查

日期 2026-11-24。基线 S11 任务书为 b884bae4。本轮按要求只审查模型和理论，不修改 S11 v0.1，不实现算法，不生成随机样本。结论先行：**幅值应允许有限结构变化，推荐单次 change-point 作为有界压力模型；这种变化和可行攻击历史集合都不是创新本身。三条理论接口可行，但后验风险外包的长时域可计算性尚未证明。**

## 一、幅值该不该变化？

应该。固定幅值 \(b\,1_{[k_0,k_1)}(t)\) 便于复用 R4a，也作为必要的消融基准；主模型若只测试固定常幅攻击，难覆盖攻击者在持续期间调整强度的场景。

但变化应由少量、预先定义的参数决定，而非任意 \(b_t\)。建议在 **S11 v0.2 候选模型**采用“至多一次幅值切换”：
\[
a_t(\theta)=
\begin{cases}
0,&t<k_0,\\
b_1,&k_0\le t<s,\\
b_2,&s\le t<k_1,\\
0,&t\ge k_1,
\end{cases}
\quad
\theta=(k_0,s,k_1,b_1,b_2).
\]
窗口采用半开端点以消除边界歧义。保留 S11 的总时长集合 \(k_1-k_0\in\{20,60\}\)，要求两个攻击段至少各持续 5 拍。建议幅值仍取 \(B=[-0.25,-0.10]\cup[0.10,0.25]\)，并设 \(|b_2-b_1|\le\Delta_b\)。候选主值为 \(\Delta_b=0.25\)，可表示同方向调整和有限方向反转；\(\Delta_b=0.10\) 可作为仅允许小幅同方向变化的敏感性模型。固定攻击是嵌套情形 \(b_1=b_2\)。这些阈值是 proposed design，尚无数据依据。

这是**有界建模选择**，不是声称普通物理载荷变化之前没人研究过。攻击幅值始终是对攻击策略预先承诺的确定参数；若 \(b_2\) 按攻击期间新息或隐藏状态在线选择，候选类需要描述策略，下面针对固定 \(\theta\) 的似然和覆盖证明不能直接套用。

### 候选核确实可逐拍写出

令 \(r=y-c_t\)、\(\nu=Cm-c_t\)、\(S_t=CP_t^-C^\top+R\)、\(\sigma_t=\sqrt{S_t}\)。事件在载荷篡改前生成，攻击的整段偏移记为 \(a_t(\theta)\)。对任一高斯分量 \(m\)，观察 send code \(j\) 的条件概率为
\[
q_{\theta,t}(1,j\mid m)=
\int_{\sigma_tJ_j-a_t(\theta)}
\phi_{S_t}(r-\nu)
\bigl(1-e^{-Zr^2/2}\bigr)\,dr,
\]
静默核为
\[
q_{\theta,t}(0\mid m)=
\frac{\exp[-\nu^2/(2(S_t+Z^{-1}))]}{\sqrt{1+ZS_t}}.
\]
由于 \(\{\sigma_tJ_j-a_t(\theta)\}_j\) 对实轴构成分割，send code 质量求和为 \(\int\phi_{S_t}(r-\nu)g(r)\,dr\)，再加 silent mass 严格为 1，包括两侧饱和码。

给定潜在精确 \(r\)，普通 send Kalman 条件更新仍给 \(N(m+K_1r,P_1^+)\)。接收端仅见 code 时，对该单元内 \(r\) 按上述截断核连续混合。幅值切换只改变当前发送单元的平移量，不在 switch 时重置或清除既往状态污染。故每个固定 event history 内仍可用共同分量协方差的高斯位置混合表示，\(b_1,b_2\) 只改变混合权重及均值路径。完整 posterior covariance 仍为分量内 covariance 加分量均值协方差。**数学递推成立，旧快速二次型似然和点创新缓存不能原样使用。**

## 二、R4a 能不能扩展到变量幅值和停止时间？

能。其原因是 Ville 定理对任何具有共同支持的合法候选概率律成立，不要求候选幅值恒定。

每个固定 \(\theta\) 由上面归一化的离散事件—码字核定义 \(P_\theta\)。给一个独立、可预测并归一化的参考轨迹混合 \(Q\)，例如给 \(k_0\) 用 \(\pi_k=1/((k+1)(k+2))\)，再对总长度、split time 和离散参考 pair \((b_1,b_2)\) 给固定正规先验。此混合是概率律，不要求包含真实连续幅值。令
\[
L_t^\theta=\frac{p_\theta(o_{0:t})}{p_0(o_{0:t})},
\qquad R_t=\frac{q(o_{0:t})}{p_0(o_{0:t})}.
\]
高斯量测、非零宽度 finite code cells 及 trigger factor \(g(r)\) 仅在单点为零，故各有限历史都有共同支持。于是 \(R_t\) 是健康律下的非负似然比鞅；对任意固定 \(\theta\)，\(R_t/L_t^\theta=dQ_{0:t}/dP_{\theta,0:t}\) 是 \(P_\theta\) 下初值 1 的非负鞅。因此
\[
P_\theta\{\exists t:L_t^\theta<\varepsilon R_t\}\le\varepsilon.
\]
自适应地删去候选盒仍可用同一保证，前提是用整个盒的似然比上界和 \(R_t\) 下界，且输出记录的 centers 来自双方共享、事件前可预测的同一 monitor 协议。

变量幅值使参考/候选维度变大，但**不会因本身时变就使 e-process 定理失效**。困难在于计算 \(L_t^\theta\) 和连续盒外包，以及长记录的混合分支数。R4a 目前只验证过固定幅值、短历史和 binary64 一次舍入；这些数值证据不能被称为 S11 finite-bit 验收。

## 三、后验矩外包是否存在？

对每个固定有限观测前缀，答案是肯定的。以 \(X_t\) 表示目标状态、\(Y_{0:t}\) 表示真实连续量测路径。给定前缀的可信 event、实际 center、code 序列，把每拍 silent 权重 \(1-g(Y_i-c_i)\) 和 send 权重
\[
g(Y_i-c_i)\,
1_{\{(Y_i-c_i+a_i(\theta))/\sigma_i\in J_{j_i}\}}
\]
相乘，记作 \(H_\theta(Y_{0:t};o_{0:t})\)。沿已记录前缀，centers 是固定的共同可见控制输入。未选择事件前，线性系统路径高斯。定义
\[
p_\theta=E[H_\theta],\quad
u_\theta=E[X_tH_\theta],\quad
V_\theta=E[X_tX_t^\top H_\theta].
\]
则
\[
\mu_t^\theta=u_\theta/p_\theta,\qquad
\Sigma_t^\theta=V_\theta/p_\theta-\mu_t^\theta(\mu_t^\theta)^\top.
\]
攻击的两段偏移只平移各段的量化单元。对任何固定有限前缀，send 单元有正宽、trigger 除单点外为正，silent 因子也正，故 \(p_\theta>0\)。被积函数受高斯一、二阶矩支配；对闭且有界的 \((b_1,b_2)\) 区间，\(p,u,V\) 关于幅值连续。因此固定时长、switch 和有限前缀上，紧参数盒存在一个正的 \(p\) 下界和有限后验矩外包。

这证明了**有限前缀可构造**，不提供数值上好用的分母下界，也不控制其随 \(t\) 的衰减。数值认证必须同时包围 \(p,u,V\)，不是拿似然区间代替状态置信区间。饱和码要对半无限单元作正态尾矩包围；不定分母、过宽区间或节点用尽时只能返回未决。

## 四、融合能保证什么，不保证什么？

对完整同一条 record，固定 \(\theta\) 下 posterior \((\mu_\theta,\Sigma_\theta)\) 的任意输出 \(a\) 都满足
\[
J_\theta(a)=\operatorname{tr}(W\Sigma_\theta)+
\|a-\mu_\theta\|_W^2.
\]
若 \(C_t\) 是覆盖真值的 candidate set，定义
\[
U_t(a)=\sup_{\theta\in C_t\cup\{H_0\}}\overline J_\theta(a),\qquad
a_t^\star\in\arg\min_{a\in\mathcal A_t}U_t(a),
\]
且可行动作集 \(\mathcal A_t\) 含 ML/基准输出 \(a^{\rm ML}\)，则
\[
U_t(a_t^\star)\le U_t(a^{\rm ML}).
\]
在 Ville 覆盖事件上，真 \(\theta_\star\in C_t\)，故
\(J_{\theta_\star}(a_t^\star)\le U_t(a_t^\star)\le U_t(a^{\rm ML})\)。
这表示最坏 candidate-risk 相对 ML 动作被控制，不表示每个真实模型下都比 ML 条件风险小。

**有一个代数反例限制逐模型保证。** 若存活集含 ML 模型本身，且基准动作正好等于该模型后验均值 \(\mu_{\rm ML}\)，则任何偏离量 \(\delta\ne0\) 使该候选风险增加 \(\|\delta\|_W^2\)。所以除非 risk gate 退回 ML，不能承诺“所有存活候选都不比各自 ML 更差”。本项目可合理承诺最坏条件风险不劣于同一候选集下的 ML 最坏风险；要证明实际 post-stop 累计 MSE 改善仍须逐 episode 试验，并计入 confidence-failure 事件代价。

## 五、竞争工作已把哪些部分覆盖了？

| 工作 | 本次核查层级 | 已覆盖范围 | 对本课题的影响 |
|---|---|---|---|
| Kurt–Yılmaz–Wang, TIFS 2018, “Distributed Quickest Detection of Cyber-Attacks in Smart Grid”, DOI 10.1109/TIFS.2018.2800908 | 已读开放全文关键模型、公式和算法。 | 攻击起点未知；攻击向量及受攻击 meter 集可随时间变化且非随机；每时刻求攻击向量 MLE，以 GLR-CUSUM 检测。分布式端用 LCSH 对本地统计量作事件式量化上报。 | 时变幅值、未知起点、量化消息、事件式通信与在线攻击 MLE 都不是可单独声称的创新。其量化对象是本地检测统计量，不是 trusted pre-attack event 后、tampered payload 的 finite-code likelihood；也未见完整攻击轨迹的全时域覆盖置信集或置信集驱动 posterior-risk envelope。 |
| Kurt–Yılmaz–Wang, TIFS 2019, “Real-Time Detection of Hybrid and Stealthy Cyber-Attacks in Smart Grid”, DOI 10.1109/TIFS.2018.2854745 | IEEE Xplore publisher abstract 和 arXiv manuscript 已查；本次未逐式复核全部证明。 | 攻击参数不作窄变化约束，在线估计未知时变参数；以 modified GLR-CUSUM 检测混合 FDI/DoS，并输出 recovered state estimate。 | “时变未知参数 + 检测 + 状态恢复”不能作为独立贡献。即使 S11 只允许一次 switch，也只是更受限的攻击族；剩余差异须对照其检测/恢复定理核实。 |
| Song et al., TNNLS 2020, “Set-Membership Estimation for Complex Networks Subject to Linear and Nonlinear Bounded Attacks”, DOI 10.1109/TNNLS.2019.2900045 | PubMed 摘要/题录。 | 未知有界线性/非线性攻击下的 set-membership state estimation 和观测器设计条件。 | “相容攻击历史/集合”和状态区间不新；统计时间一致覆盖是潜在区别，不是集合概念本身。 |
| Degue–Le Ny–Efimov, Automatica 2022, “Stealthy Attacks and Attack-Resilient Interval Observers”, DOI 10.1016/j.automatica.2022.110558 | 出版社摘要/文章页；本轮未逐式审计全文。 | 有界扰动下构造 stealthy attack sequences，并设计 interval observer 估计状态和攻击界。 | 确定性 feasible stealth-history 与区间恢复已有近邻；需对比有限码联合似然与统计覆盖的实际增量。 |
| Li–Hu–Guo, JFI 2024, “State Estimation for Linear Discrete-Time Systems with Binary-Valued Quantized Innovations Against Data Tampering Attacks”, DOI 10.1016/j.jfranklin.2024.106817 | 仓库已有出版社全文模型与定理核查。 | 二值量化新息下的篡改、攻击策略估计和补偿。 | 有限量化、攻击参数辨识、补偿都不能单独主张。 |
| Li–Hu–Guo, IEEE Sensors J. 2024, “Fusion State Estimation of CPS Under Quantized Observations and Tampering Attacks”, DOI 10.1109/JSEN.2024.3393725 | 本次只核题录及索引摘要，全文 OPEN。 | 摘要称多传感器部分量化通道遭篡改；未知策略下联合估计策略和状态。 | 与量化攻击融合直接重叠，必须取得全文才可作公式级差异声明。 |
| Li–Hu–Guo, Ad Hoc Networks 2025, “Transmission Scheduling for Remote State Estimation with Quantized Communication Against Tampering Attacks”, DOI 10.1016/j.adhoc.2025.103997 | 仓库已有出版社全文 theorem-level 审查。 | 二值通信、选择性 tampering、策略识别、状态补偿和辨识/估计通信调度。 | 识别结果驱动补偿与调度不是本文新点。其优化目标不同于全时域 trajectory coverage + fixed-record posterior-risk envelope。 |
| Li–Xue–Zhao–Guo, IEEE TSIPN 2026, “Remote State Estimation With Quantized Communication Against Markov Tampering Attack”, DOI 10.1109/TSIPN.2026.3672342 | 本次只核题录及摘要，全文 OPEN。 | 二值量化、Markov 篡改、MMSE、已知策略补偿、未知策略联合辨识/估计和调度。 | 与 “量化攻击识别后恢复” 极近；不能写“首次”。其统计时间一致参数集和对同一完整记录的风险 envelope 关系尚待全文核对。 |
| Liu–Li–Guo, Ad Hoc Networks 2026, “Remote Estimation with Binary-Switching Sensors Under Tampering Attack: Identification-Compensated Method Using Quantized Communication”, DOI 10.1016/j.adhoc.2026.104269 | 出版社摘要。 | binary-switching sensors、量化 tampering、未知策略识别、补偿，并讨论达到指定识别精度所需数据量。 | “达到精度的识别样本数 + 补偿”已有直接近邻；审计覆盖和 posterior-risk 是否不同需全文核查。 |

## 六、创新性裁决

1. **不采用“攻击幅值可变”作创新点。** TIFS 2018 的 \(a_t\) 已是时变向量，且攻击节点集也随时变；piecewise two-level 是其受限子类。引入一个 change point 可提升 S11 行为代表性，但不是新算法。
2. **不采用“可行攻击历史集合”作创新点。** set-membership、interval observer、GLR/CUSUM 和量化下联合攻击/状态估计均有大量先例。
3. **唯一值得进一步检验的贡献假设**是：在本任务严格权限下，用可信的事件前随机触发记录与被篡改后 finite-bit payload 构造正确的码元联合核；对有限 piecewise attack trajectories 建立 candidate-specific、uniform-in-time confidence set；再将其传入同一完整记录上的 conditional-risk envelope，从而约束 ML 点估计/补偿的模型错选风险。
4. 这仍然可能被审稿人评价为序贯置信工具与 robust/Bayesian model uncertainty 的组合。要站住，必须有直接定理和消融证据显示：相同记录、相同检测结果下，confidence-constrained minimax action 的最坏风险 upper 严格低于 ML 单模型；以及数据证明 post-stop MSE 有收益。
5. 2018 TIFS 论文全文涉及 event-driven sampling，但其 LCSH 量化的是 local detector statistics；不是 S11 的“原始可信触发在被攻击 payload 之前产生，攻击后有限码元按 \(I_j-b_t\) 计算”。2019 TIFS 摘要还包含未知时变参数估计和恢复状态输出。这些合同差异是待核边界，不能直接推出新颖性。
6. 2024 IEEE Sensors J.、2026 IEEE TSIPN 与 2026 Ad Hoc Networks 目前为摘要/文章页级对照，全文级比较仍 OPEN。v0.2 在该门通过前不进入实现，也不作全球“首次”声明。

## 七、建议的 S11 变量幅值 amendment

保持“至多一次变化、攻击者事前承诺路径”，而不是自由 \(b_t\)：
\[
a_t(\theta)=
\begin{cases}
0,&t<k_0,\\
b_1,&k_0\le t<s,\\
b_2,&s\le t<k_1,\\
0,&t\ge k_1.
\end{cases}
\]
总攻击长度先限 20/60 拍，两个段各至少 5 拍；\(b_1,b_2\in[-0.25,-0.10]\cup[0.10,0.25]\)，\(|b_2-b_1|\le0.20\)。固定幅值 \(b_1=b_2\) 是 nested baseline。建议 v0.1 固定幅值集合保留为受限攻击 ablation，主幅值模型改用一次 change-point；\(\Delta_b=0.10\) 作为变化幅度敏感性，不另扩充全套压力矩阵。若不需要方向反转，可收窄幅值集合到同号两段。

这是**待批准的协议修订建议**，本报告没有修改 S11 v0.1，也没有实现新模型。若采用，先更新 protocol、候选维度、reference prior、样本量/复杂度门槛和来源清单，再进入 S11-A。

## 八、当前阶段门

先完成以下理论/算术小门，再决定实现：
- R1：上述 two-level kernel 归一化、切换/停止后的 mixture recursion 与共同 center filtration 证明。
- R2：固定 \((k_0,s,k_1,b_1,b_2)\) 的 2–5 拍 finite-code likelihood 及 \((p,u,V)\) 独立外包。
- R3：reference prior 对未知 onset/switch/stop 的归一化和 Ville 置信覆盖；验证任意数据依赖 box pruning 的 upper/lower 判据。
- R4：同一历史下 ML、全 posterior mixture、confidence-set minimax 三者条件风险逐项对照，先给理论不退化条件和具体小模型证人。
- R5：竞争全文审查，尤其取得 IEEE Sensors 2024 与 TSIPN 2026 全文，及核对 2019 TIFS/2026 Ad Hoc 的具体信息集和风险量词。

只有 R1–R4 可闭合且 R5 未发现同等覆盖结果，才恢复 S11-A 实现。**本轮没有代码实现、S11-A、数值试验或随机样本。**
