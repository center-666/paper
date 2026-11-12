# FDI / Replay小问题筛选

研究目标是一篇增量型学报论文。根据完整文献复读和已做实验，现只留两个问题候选，不预设必须解决两类攻击。**首推候选1，但先做文献/最小复核门槛，未达到前不写论文。**

## 结论先行

最值得先用现有工程验证的是：

> **接收端重复使用同一邻居估计缓存期间，能否把多个新本地量测形成的相关证据按整个缓存驻留episode校准，识别持续FDI并控制实际估计损失；相对于适配到同一信息和FPR口径的UIO、window χ²和跨包CUSUM是否有增量？**

理由是它有明确可写的共同误差来源、能复用项目实现、此前强step有小幅可重复信号；研究缺口具体，但与Liang–Liu 2023的事件触发UIO相当接近，不能先宣称新颖。若这条对照输掉，停止。历史包字典选择型Replay列为第二候选/强压力攻击，因为它还没有闭环损伤证据。

## 候选1：episode级持续FDI验证（首选筛选）

### 最近方法

| 文献 | 已有方法与理论 | 对当前候选意味着什么 |
|---|---|---|
| Zhou et al. 2022 Automatica 138:110151, Thm.1–3 | 本地量测残差对邻居estimate做空间χ²滑窗；秩亏时存在空间零方向攻击；独立指数门限保护并维持Gaussian递推 | 直接强基准；它的结果主要针对每次保护决策及协方差，不是packet cache episode的风险分布。要查其滑窗在ZOH重复缓存和随机门限下是否已可直接推广 |
| Liang & Liu 2023 IEEE TIM 72:3520111, Theorem 1–3, Algorithm 1 | 事件触发MAS；接收端用UIO对邻居ZOH输出产生adjacent residual；H∞优化显式建模触发误差 | 最危险近邻。它已“缓存保持+后续动态残差+attack detection”。需要把对象差别具体化：该文为物理耦合agent输出；本系统为多节点观测共同状态、发送local state estimate且receiver每步有独立本地measurement。差别是否足以导出不同定理尚未确认 |
| Tunga et al. 2018 ACC:1752–1757, Thm.1/Propositions 1–2 | Static χ²、CUSUM、window χ²，目标FAR解析校准，并分析零报警攻击的估计偏移 | 窗口/序贯统计及误报控制不是新方法；须用与该基线相同的episode误隔离率和完整相关协方差比较 |
| Qian et al. 2023 IEEE TAC 68:6361–6368, Thm.1–2 | 触发选择下innovation的条件期望和条件误差协方差 | “触发数据有选择偏差”已有正面统计理论；但没有攻击或共享邻居缓存 |
| Güzey & Güzey 2026 SMP&T 152:103318, Lemma 3.1/Thm.3.2 | NIS、χ² likelihood、leaky trust、hysteresis/recovery、hold-last bearing Replay、WLS/IRLS，50-MC与消融 | trust/history/recovery的组合已存在，架构是融合中心；不能以中心化不同就忽略，需适配结构比较或说明成本 |
| Zhang 2024 Electronics Letters 60(6); Peng 2025 IEEE Sensors J. 25(15) | 参数估计领域的temporal reference、空间中值、adaptive correntropy和经验threshold | “时空参考+统计权重”不能做成泛化贡献；两篇不是动态Kalman同对象 |

### 具体缺口（待确认）

设节点i收到邻居估计\(\tilde m_j(t_r)\)后，在下次成功收包前继续用缓存，年龄a时可形成
\[
r_a=y_i(t_r+a)-H_i A^a\tilde m_j(t_r).
\]

在缓存攻击偏差b固定的简化情形中，均值部分含\(H_iA^ab\)；所有年龄残差共享缓存初始估计误差，且过程噪声经A跨时相关。若把L个r_a当独立样本做滑窗χ²/CUSUM，会错误累计证据。严格方法需要使用同一实际发送规则、同一packet cache的联合残差covariance/条件分布，按完整episode首次误隔离率标定。每个新包会重启episode，最后一个不完整episode需要正确右删失处理。

在限定的简化分析中，令\(q_r=x(t_r)-\hat x_j(t_r)-b\)，未来过程噪声独立于q_r，则
\[
r_a=H_iA^aq_r+\sum_{s=0}^{a-1}H_iA^{a-1-s}w_{t_r+s}+v_i(t_r+a).
\]
条件于packet/send history后，若q_r仍是均值m_q、协方差P_q的Gaussian，残差均值是\(H_iA^am_q\)，joint covariance的(a,c) block为
\[
H_iA^aP_q(A^c)^TH_i^T+
\sum_{s=0}^{\min(a,c)-1}H_iA^{a-1-s}Q(A^{c-1-s})^TH_i^T+
\mathbf1_{a=c}R_i.
\]
这是状态方程的协方差传播，不是对Send-on-Delta选中样本Gaussian的无条件主张。确定性/随机触发条件、发送估计误差与receiver自己的过滤历史可能改变q_r的条件分布和cross-covariance；最小复核必须先在真实事件协议下测/推这一分布。若采用经验联合校准，episode最大值阈值只提供数据集上的目标误隔离频率，不自动给分布无关或跨时的概率保证。

【L】Tunga处理标准滑窗统计；Qian处理触发条件矩；Liang处理事件触发与ZOH误差的UIO残差。它们不能只靠题名排除，也不能不核逐条假设就说已完全覆盖该共同缓存目标。尤其Liang是最近直接架构性先例。本候选的新颖性为**U/H**，不是已成立。

### 最小改进机制（不是新算法承诺）

只在同一receiver和同一cache episode中，比较完整joint-covariance GLS/common-offset likelihood与instant residual、window/CUSUM；若统计假设经验证，再在独立clean calibration episodes上按prefix最大值选门限，以估计“每个完整packet驻留期至少一次误隔离”的频率。检测后隔离当前缓存至下个可信新包，可作为独立融合消融。先不加神经分类器、额外攻击分类或水印。

该做法本身仍可能只是标准GLS/scan statistic的一个应用；要先用最小验证证明它比现有UIO/window/CUSUM更贴合该共享缓存误差，并改善真实损伤。

### 最小验证

1. 固定相同真实发送机会和packet schedule，避免检测器改变发送次数；攻击仅在真实send后替换一次包，后续hold到下一正常包；分别测step bias、half/low bias、Replay旧estimate。
2. 攻击者不得看receiver当前量测/真值/未来。Replay来源只允许edge上实际截获的历史发送包。
3. 对照local、Yang-form raw、Zhou 2022随机保护、instant residual、相关window χ²、energy/signed CUSUM、UIO机制移植，以及episode共同偏差统计。门限在独立clean tune split上匹配episode-FPR目标，另用不参与选参的clean audit split报告不确定性；经验匹配不写成形式概率保证。
4. 主要指标：完整episode false isolation、attack episode detection delay、receiver attack/recovery-window MSE、正常MSE、通信包数与字节。FPR和MSE同时报告，不把高检测率换算成因果防御保证。
5. 用新的独立种子；所有方法共用state/noise/schedule作paired比较，以seed为统计单位。先小规模确认，再决定是否扩大，不能复用旧test选门槛。

**继续门槛：**强持续偏置以外，至少还有一个预先指定的持久/重放场景在相同episode-FPR下得到实用MSE或检测延迟改善；改善不能全由较保守的隔离或更高发送数解释；且Liang UIO适配后仍有清晰差异。若无，停止。

### 缺陷和风险证据分类

- **文献已证明【L】**：状态差χ²存在rank-deficient blindspace（Zhou）；单节点K-means/信任及历史恢复已有多种方法；触发窗口残差需纳入通信误差（Qiu/Liang）；窗口χ²/CUSUM是标准基线。
- **项目已有实验【E】**：interval-tail主比较9项0项通过；完整cache-mean序贯门槛1/4失败；CUSUM保留状态后强step仍局部3/4，但half-step不成立；部分可观主边step 4/4未过。
- **由模型可推导【M】**：同一缓存误差在episode内是共同随机量；如果独立样本模型忽略该协方差，p值/FPR会失准。准确协方差仍要含触发选择与网络滤波cross-covariance。
- **尚待实验【H】**：利用这结构能否在同episode-FPR、同消息机会下胜过适配后的UIO/window/CUSUM，并改善实际MSE。

## 候选2：历史状态包字典内的选择型Replay（强压力问题）

### 具体问题

攻击者在链路j→i上仅能把当前实际广播的estimate替换为该sender过去真正发出的estimate之一：
\[
\tilde m_j(t_r)\in\mathcal D_j(t_r)=\{m_j(s):s<t_r,\ j\text{在} s\text{确实发送且该包被截获}\}.
\]
攻击者知道自己的packet dictionary、公开A及公开检测器，但不知接收者当前y_i和真状态。问题是：在固定替换次数/发送机会下，挑选型Replay是否比固定滞后、最近邻、周期片段在闭环中制造更大MSE，同时降低现有空间/时间统计的检出率？

### 最近方法与明确差异

- **Huang 2024**周期重放多传感器measurements，稳定/不稳定系统下分析误差与KL残差；输入字段不是邻居estimate。
- **Yu 2025**使用实时receiver estimate构造reflection attack；攻击者当前信息强于有限历史packet dictionary。
- **Xing 2025 / Ge 2026**截获历史innovation并可线性组合当前innovation、加攻击噪声，在KL/Covariance约束下优化；不是只允许原样重放。
- **Su 2022**多sensor measurement重放靠不可篡改source labels；本项目不假定该安全字段。
- **Mitra AoI 2022**处理可被伪造的age和Byzantine节点，需多跳拓扑冗余；不是本项目局部字典检验。

### 已有探针和真正缺口

旧dictionary probe用64个seed、两种感知模型，在冻结normal sender traces上挑最多64个历史真实包，攻击函数仅看当前发送估计、历史包及时间、last delivered payload、公开A/H和标定常数，不看receiver y/x/future。risk-greedy降低可疑评分proxy，但异质模型只在约16%–19%攻击机会选择替换。它是offline selection/one-step influence proxy，未重放到真实闭环网络估计器，也未证明实际MSE或检测改善。

【L】Huang/Yu/Xing/Ge都有时间历史或Replay相关攻击，但信息权限分别是历史measurement、实时receiver estimate、可合成历史innovation；【M】如果方法测试无攻击者可见性的receiver当前残差，便偷换了攻击能力；【H】合法字典选择可能利用时间残差与空间残差的联合盲区，现无闭环结果。

### 最小验证与停止门槛

旧五节点发送历史直接作为攻击者可见字典；重跑新独立seed。只设fixed lag、random legal history、nearest-to-current sender packet、公开proxy筛选四种策略。所有payload必须带原始source time和发送证明；比较相同替换次数，另列攻击者不得读到的量。先固定外生日程评估，再仅对有信号策略闭环运行。报告实际接收MSE、space/time score、消息数、来源年龄和恢复窗。如果最大损伤策略只是低发送机会或极端选择且现有接收者完全无法识别，就应报告被动防御边界，不继续发明更复杂权重。

这项适合作为候选1的强攻击压力场景；单独一套攻击搜索器未必构成防御型学报贡献。

## 为什么不列第三个“空间+时间信任算法”

该拼接的各层已有近邻：Zhou空间残差、Yu反射盲点、Güzey/Nosal时间信任/恢复、Wang饱和、Zhang/Peng时空参考、Tunga窗口CUSUM。项目interval-tail、reference-reset与partial-observability结果也未通过门槛。不能仅改权重公式或检测名称来重开。

## 推荐与不确定性

先做**候选1的文献排除+最小同风险验证**，同时用候选2构造最强但权限明确的Replay stress case。候选1有重复强step信号，但最近的Liang UIO和标准GLS/episode最大值校准带来很高新颖性风险。若他人可从其公式通过同一prediction/cache state直接得到本检验，或经适配后性能不增，结论应是“无独立增量”，转为旧方法比较/停止，而非追加模块。

当前判定：问题值得一次有限筛选；**尚不能回答它足以支撑一篇学报论文**。先证伪，后选题。
