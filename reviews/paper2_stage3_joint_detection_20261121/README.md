# 第二篇论文阶段 3：可信事件、载荷与量化中心的联合检测

基准提交8c02c07b；日期2026-11-21。本包建立原标量量化远程估计场景的联合检测模型，保持原攻击权限和反馈协议，仅改变接收端如何利用已有记录。正式论文未修改，恢复仍未实施。

## 理论与算法

- [执行范围与信息合同](00_scope_and_algorithm_contract.md)
- [精确联合核、候选滤波、Fisher与二阶KL](01_joint_observation_theory.md)
- [联合/条件载荷/校正创新算法与误报保证](02_algorithms_and_guarantees.md)
- [确定性核验及数值边界](03_deterministic_validation_plan.md)
- [候选失配与健康保证的独立复核](04_independent_math_review.md)
- [无界联合似然的半阶矩延迟证明](05_fractional_moment_delay.md)
- [半阶矩证明的独立审查](06_fractional_moment_review.md)
- [中心/码字权限条件核与信息界](10_center_vs_codeword_likelihood.md)、[确定性检查结果](phase_visibility_checks.json)
- [中心精确可见与码字索引记录的信息模型](11_phase_visibility_addendum.md)
- [相位权限推导的独立审查](12_phase_visibility_review.md)
- [独立确认实验与决定](07_results_and_decision.md)
- [近邻与创新边界](08_novelty_boundary.md)
- [幅值失配下的低阶分数矩分析](09_offgrid_fractional_moment.md)

联合模型保留了发送选择因子。发送时不能只使用高斯创新密度；而且事件与同拍载荷不能未经条件化当作两个独立证据相乘。本包提供精确事件×条件载荷分解，并以正确选择校正的创新倾斜作为对照。

部署J1使用O(J)可预测候选与起点/强度混合，健康下有全时域误报保证。它不是每个未知物理起点各自重置滤波的完整贝叶斯似然。真实幅值匹配时，初始化失配几何衰减；半阶矩分析给出覆盖该实现的有限检测延迟证明，但未给数值认证的统一延迟常数。

在含匹配候选的小幅值模型族中，联合信息为二阶，充分延迟具有b⁻²尺度并包含混合权重代价。该理论不把固定三档网格假装成覆盖所有任意小幅值，网格外性能另作独立实验。

## 实验与复现

[protocol.json](protocol.json)和[freeze.json](freeze.json)固定所有性能输入；运行入口为[launch.py](launch.py)。24组初筛各5,000条，24组独立确认各50,000条；四组网格外压力测试各20,000条；两模型各5,000/50,000条8192拍健康筛查/确认。共1,510,000个独立episode，嵌套时域不重复计数。

运行环境为Python 3.11.18、NumPy 2.4.6、SciPy 1.17.1。绘图使用Matplotlib 3.11.2。核心输入哈希在冻结记录中；实验保留既有输出拒绝覆盖策略，重跑需独立研究副本与新的run身份。汇总保留每指标n、sum、sum_squares，支持重新计算episode标准误；不将时序相关样本当作独立观测。

[参考积分](joint_reference_checks.json)与[实际core核验](joint_kernel_checks.json)包含归一化、选择校正MGF、Fisher/局部KL、显式起点和、静默屏蔽及密度零点检查。代码未以epsilon修改密度。误差坐标沿用阶段2代数等价实现，避免U1巨大绝对状态消减。

[单接收端原型](receiver_detector.py)和[使用说明](receiver_usage.md)只使用接收端已有信息，已与冻结J1做固定输入逐拍一致性检查。[半阶矩独立积分](fractional_moment_checks.json)和[近零点精度审查](precision_sensitivity_note.md)分别验证理论代数与数值实现的适用范围，不替代有限字长安全证明。

## 研究判断的约束

必须区分相对事件-only的收益、相对校正创新的收益，以及联合J1相对条件载荷P1的增量。如果P1与J1接近，应据实说明主要收益来自选择模型下的载荷信息，不能把全联合架构包装成已验证的额外优势。

当前日志在接收端已经可用，不新增上行测量；外部审计日志传输、有限字长和实际硬件成本未验证。联合核对固定已知中心也可成立，因此不能把全部收益归因于随机量化。标准e-process、条件似然、Fisher分析和分数矩工具不单独算新算法。

本轮只检测，总MSE仍由共用monitor决定。报警前MSE只是未来可能门控的暴露指标，不代表已实现可信恢复或实际降损。模型失配、离散载荷、主动探测及恢复策略需另建协议验证。
