# G1决策：缓存episode候选

日期：2026-11-12。

## 唯一推荐

# **B：统计问题存在，但方法创新不足，不建议作为独立论文主贡献。**

核心原因不是 episode 残差不相关，而是项目已有序贯检测器已经用完整经验联合prefix covariance计算共享常值缓存偏差的Wald统计，并用episode最大prefix分数设阈值，再把alarm状态保留到下个新包。候选的“GLS/episode max/cache isolation”主要机制因此已实现。真实触发下统计分布仍待核查，但把外生固定日程改成Send-on-Delta闭环属于协议适配，不自动成为新方法。

简化模型中，若cache误差e是未知episode截距而攻击偏置b也未知，数据只依赖e-b，二者严格不可分。若e是已知零均值Gaussian随机效应，GLS对b的信息随episode长度增加但趋于1/var(e)。这有分析意义，却是标准随机截距统计模型，不是新distributed filtering算法。

## 旧实现等价性与保留差别

现有代码对长度L残差prefix d作
\[
T_L=d^TC_L^T(C_LS_LC_L^T)^{-1}C_Ld,\quad C_L=[I,\ldots,I]/L,
\]
其中S_L是完整经验联合协方差。相当于共同常值residual offset的covariance-normalized prefix-mean Wald test。CUSUM和白化window也已运行。它不是任意动态模板下无约束GLS的逐数值复现；但将响应改为X_L=[H;HA;…]后做matched GLS/GLRT是标准方法，目前没有新的保证或实测收益能支撑独立立项。

Liang–Liu UIO原定理不适用于该架构：原论文是连续物理MAS，每个agent重构耦合邻居agent的ZOH输出；本项目是多个节点观测共同状态并交换各自Kalman estimate。需要新增增广状态及rank条件才能适配。本轮没有做UIO复现，也不假装公平比较已完成。即使不考虑该近邻，原full-covariance prefix score已经触发G1停止条件。

## 门槛状态

1. 相关GLS/episode max已基本实现：**满足停止条件1**。
2. 真实Send-on-Delta survival条件分布：未解析；旧G1运行用固定gap schedule。经验模型不迁移为精确Gaussian保证。
3. 强持续偏置有局部结果；half/low、Replay及主边部分可观测没有稳定增益。
4. 同机会、episode风险条件下，旧完整场景门槛1/4失败。跨包CUSUM后step仍局部3/4，但half step接近零。
5. 正常MSE代价尚非主要失败原因；仍需分phase/FPR完整报告。
6. 对原外生日程对照没有增加发送机会；闭环SoD候选尚未试，不能说已公平验证。

任一停止条件满足即可停止，不需要等待更多数值搜索绕开条件1。

## 样本量精度

用旧192个独立种子配对差方差作只读规划：要分辨1% receiver attack-window MSE改善，正态近似、80%功效下，单一双侧comparison约需339–1266个独立seed；若按12个family比较用保守Bonferroni约需592–2215个。见g1_sample_size.json。这个计算不是保证，且未来GLS统计量方差可能不同；但说明新实验不是轻量“几十seed复查”。episodes和时间点不能当独立样本。

## 本轮决定

根据G1停止条件1，**没有启动新seed仿真**。不再加trust、clip、watermark或恢复模块。本轮只保存代码复核、episode长度/右删失审计、理论可辨识性和样本量精度。候选的统计现象可作为负结果或方法比较写入项目总结，不能作为已发现新方法提交。若将来转为论文审计/比较研究，须另行立项且重新定义贡献和统计问题。
