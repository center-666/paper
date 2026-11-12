# G1任务二：episode候选与已有基线的等价性审计

日期：2026-11-12。只读核对源代码、预注册配置及既有运行，没有生成新轨迹。

## 1. 旧episode统计器的真实计算

来源：simulation/sequential_cache.py:36–80中的PhaseStatistics.fit，:87–117中的current/episode_scores，:127–190中的episode更新、跨packet reset和episode完成；simulation/engine.py:60–65 Send-on-Delta，:71–104攻击顺序，:106–139 cache/monitor时序。

长度L的缓存前缀残差展平为d=r_{0:L-1}-mu_L，训练数据给出的完整经验联合协方差为S_L。代码采用算术前缀平均矩阵C_L=[I,...,I]/L，其covariance为C_L S_L C_L^T，实际score为
\[
T_L^{mean}=d^T C_L^T(C_L S_L C_L^T)^{-1}C_Ld. \tag{4}
\]
这是完整协方差归一化的常值共同偏移Wald统计量。不是只对白化各年龄的边际方差，也不假设前缀点独立。

必须避免过度声称：任意S_L下最优GLS共同均值权重是
\[
\hat b=(X^TS_L^{-1}X)^{-1}X^TS_L^{-1}d,\qquad X=\mathbf1_L\otimes I_m.
\]
代码的算术平均在交换/等时模型可能与它相同，但一般不等于该不受约束的GLS。既有steady主边age2–8下两者算子相对差约6.5%–27.5%。因此，完整动态响应模板的标准GLS数值未被旧mean逐字实现；但它只是对已知模板的Wald/GLRT变体，不是已经发现的新机制。

对于实际主边0到1，gap8 steady训练/校准age 1到8分别各有4032个完整候选episodes；irregular分别为8160、7392、6624、4224、2592、2592、864、864。全部大于完整协方差门槛40，未用逐时block-diagonal fallback。age9-10没有数据，标为fallback；两条旧主schedule最大age是8。因此“candidate尚缺完整缓存协方差score”不成立。

阈值是完整正常episode所有prefix最大值的经验95%分位（sequential_cache.py:55–62）。之后normal tune独立于train/calibration，用四轮分位数调整（run_sequential_validation.py:54–65及注册计划threshold_tuning_rule）；normal audit和test再独立检查。bad标记在一个缓存episode内累计（sequential_cache.py:168–176），一次报警后隔离至下个fresh包；fresh到达先结束旧episode再重置统计量（:139–146）。最后没等到fresh的episode标右删失（:178–183），旧校准和FPR分母排除该episode。该校准是经验性的，不是finite-sample、distribution-free或always-valid保证。

原事件与通信条件：线上引擎在攻击前以触发发送estimate、之后ZOH缓存和A^age外推；但G1序贯运行为了同机会对照，计划使用固定外生gap8和irregular schedule，而不是闭环Send-on-Delta。Local measurement仍每tick可用。原名义Kalman增益按q=1全边通信联合协方差设计，然后复用于触发/cache runs。不能说G1序贯结果已经证明了实际Send-on-Delta闭环下的统计有效性。

## 2. 与竞争基线的等价关系

### Zhou 2022随机保护

不与episode统计器代数相同。Zhou逐步按接收端估计差使用指数随机门控，条件接受概率为exp(-distance平方/nu)，并维持其Gaussian递推/谱稳定条件；不是joint-cache历史GLS。但是已是直接信息与架构基准。项目中Zhou随机门使用同一接收节点当步的共同随机门，已做移植。比较须同发送机会、同正常误隔离风险、同payload/计算字节。

### Tunga 2018窗口Chi-square和CUSUM

统计机制高度重合：残差能量/白化prefix/时间窗口累积、目标FAR校准均为标准方法。G1代码已覆盖full-prefix covariance whitening、fixed white window、energy CUSUM、signed CUSUM、episode max calibration及whole-cache isolation。换成一个dynamic response matrix仍是标准GLS/scan statistic，需要证明它解决了旧statistic做不到的攻击可辨识性，而不能只宣称公式更匹配。

### Liang–Liu 2023事件触发UIO

原文连续时间MAS有physical coupling states，节点由当前测量事件触发发送输出，邻居用ZOH保持，并通过UIO估计某个物理邻居agent状态、构造adjacent residual；UIO existence依rank/dependability条件，设计显式折中attack/fault敏感度与trigger error的H-infinity gain。

不能直接迁移原定理：项目各节点测量同一共同状态x，并交换各自Kalman estimate；没有原文中的sender-local plant output/unknown-input耦合结构。若把estimate cache当作UIO对象，需要新建sender estimator误差状态，把innovation、估计噪声和网络共识误差写进增广系统；payload attack与通信输出在同一信道，是否可解耦须重推rank条件。当前未完成此适配，不能声称已公平胜过UIO。但UIO不能直接套公式，不足以证明该候选新颖。

## 3. 明确哪些是标准工具，哪些可能不同

以下是标准或已有实现：受攻击状态估计分解、prefix平均Wald/GLS、Mahalanobis whitening、滑窗max扫描、CUSUM、episode内alarm OR/缓存隔离、按独立正常episode经验校阈。

可能结构差异是Send-on-Delta之下，estimate cache误差跨多次本地measurement共享，且cache survival/episode结束由网络触发机制选择。此选择可能使joint residual conditional law非Gaussian。候选如果只是把现有固定外生日程episode-GLS搬回闭环SoD，并用经验协方差重新标定，属于标准数据/机制适配；需要证明它对应一个可辨识且有性能代价差的新问题。不能把闭环测试未完成说成旧理论没有该功能。

候选1的实质缺口不是“没有联合协方差GLS”，而是：真实Send-on-Delta条件下episode分布和误隔离是否可校准；缓存攻击偏置相对sender估计自然误差是否可辨识；同一机会、风险与消息量下是否超出旧mean及CUSUM。这三点都未在实际闭环协议中成立为结果。
