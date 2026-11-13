# G4直接竞争方法矩阵与全文核读

基准提交：`ce5923164aee083769eb5f5b2bfb8af1c4585124`。核查日期：2026-11-13。本文只审查A/B/C/D/F的直接替代风险，不是全领域新颖性证明。编号页码均为本地PDF页，必要时同时列正式页码。`FULLTEXT`表示本轮阅读了相关原式与假设；`ABSTRACT`表示仅完整摘要；`PARTIAL_ABSTRACT`不可支撑算法级判断；`METADATA/UNVERIFIED`不提供定理结论。

**最重要的排重结论：主动恢复、重传历史包、迟到校正、重新信任、按通信收益决定发送都已有直接先例。** 本项目只能争取具体缓存协议、有限预算和可验证风险约束下的新能力，不能把底层工具重新命名。不同架构不等于没有竞争；反过来，已有连续观测器或控制定理也不能不核条件就宣称覆盖当前Yang稀疏缓存协议。

## 1. 对照总表

|文献与证据等级|实际攻击入口/信息|具体机制及可保证对象|对本候选的替代性|
|---|---|---|---|
|Nasiri, Seifi & Delkhosh, IEEE TSG17(1),562–575,2026；[DOI](https://doi.org/10.1109/TSG.2025.3609891)；FULLTEXT|电网区域观测/状态估计受FDI；互换观测、预测量、共享状态及trust投票|G-DIKF：trust加权Huber批回归、IRLS及内外邻居迭代；PDFpp6–8式(28)–(46)。IEEE14/118bus恢复实验；本轮未找到编号的全动态均方恢复定理|直接竞争B/C，也竞争A的选择性保留。它已经是状态恢复，不只是trust重新变大。尚未核见固定额外字节预算内选择刷新时刻的保证。|
|Xu, Wang, Yan & Gao, IEEE TNSE13,2852–2870,2026；[DOI](https://doi.org/10.1109/TNSE.2025.3621283)；FULLTEXT|邻居预测状态及上报协方差均可篡改；请求指示包另假设安全；重传包仍可被攻击|DRR：可疑包仅请求重传一次；当前检测、重传检测及历史校正；PDFpp5–7式(12)–(20)；p9 Theorem1条件下均方指数最终有界；后续延迟分析|直接竞争B/C与备用协同验证。主动请求、额外消息、历史包重算不是新机制；原始sender留存与安全请求是明确额外资源。|
|del Nozal et al., IEEE CSL6,506–511,2022；[DOI](https://doi.org/10.1109/LCSYS.2021.3082309)；FULLTEXT|攻击/故障agent经邻居传送估计；多跳可观测分解；可重新执行setup|置信/警戒/不信任区间及更严格re-trust区；PDFp4 Def5式(9)、TableI；p5 Theorem1式(13)用共同二次Lyapunov/LMI保证指定trust切换范围内稳定；HIL|C“滞回+恢复接入”已有直接完整方法；A按可观测子空间分配邻居信息也已有强先例，不能只改名。|
|Zhang & Yang, JFI363,108914,2026；[DOI](https://doi.org/10.1016/j.jfranklin.2026.108914)；FULLTEXT|交换字段改为本地residual；异构量测维数；攻击者可有/无实时残差访问|正则化映射残差、窗口χ²和可选私有水印；PDFp3式(3)–(7)，p5 Thm1一步最优增益，p6 Thm2在Assumption3下正常均方有界；pp7–8 Thm3/4分别是独立偏置及反射型攻击统计量期望增量|备用协同验证和A的强比较。额外残差需计字节；不能把其正常有界性误写成任意FDI/Replay下全局安全保证。|
|Yang et al., Automatica50(8),2070–2076,2014；[DOI](https://doi.org/10.1016/j.automatica.2014.05.025)；FULLTEXT|资源限制、随机传感器激活；无攻击；随机激活同时影响量测及估计交换|最优局部增益、全网络交叉协方差，激活率/一致性参数与误差界；PDFpp4–6 Lemmas7–9、Theorem1|Yang基准及“资源—估计质量调度”的直接标准工具。当前每拍量测、缓存外推实现不等于原文全部假设。|
|Yang et al., Automatica102,34–44,2019；[DOI](https://doi.org/10.1016/j.automatica.2018.12.027)；FULLTEXT|邻居状态估计通信FDI；基于Yang结构的攻击/防护|分布式受攻击估计及检测/保护；原状态更新及交叉协方差是当前骨架来源|A/B/C均须保留的基准；不能通过削弱本地增益创造保护缺口。原稿时序不是另加独立Kalman predict。|
|Zhou et al., Automatica138,110151,2022；[DOI](https://doi.org/10.1016/j.automatica.2021.110151)；FULLTEXT|邻居当前状态估计FDI；接收端私有随机阈值|PDFpp4–5式(20)–(24)：指数随机阈值，接纳概率exp(−‖disagreement‖²/ν)；Thm2是原文安全定义及谱条件下结论，Thm3给其特定模型的协方差分析|所有候选的强保护基线。项目中加cap/缓存/名义增益后只称结构适配，不能直接继承原全文高斯性和安全性结论。|
|Deghat et al., Automatica99,369–381,2019；[DOI](https://doi.org/10.1016/j.automatica.2018.10.052)；FULLTEXT作者稿|节点观测器加性偏置输入；p3 Remark也将链路估计篡改纳入输入通道；原量测及额外邻居检测器信息|作者稿pp6–9 Thm1–3、式(18),(29),(30)：耦合LMI/H∞跟踪器，校正估计xhat+ehat；对admissible bias类及L2扰动给渐近恢复/能量界|已有攻击输入跟踪与当前估计修正。B若仅增加observer抵消污染则不新；离散年龄缓存/持续白噪声不能直接套连续L2结论。|
|Tabatabaei et al., Automatica180,112460,2025；[DOI](https://doi.org/10.1016/j.automatica.2025.112460)；FULLTEXT|LSS子系统间传输输出受FDI；本地物理输出、耦合模型及邻居模型|PDFpp3–10，级联UIO/Luenberger；Thm3.1重构非隐蔽攻击/真实输出，Thm3.2补偿稳定性，Thm4.1/Props4.2–4.3处理隐蔽类的部分/全重构条件|A/B/C不能宣称首次通信数据重构并恢复。它不免费提供本项目原始健康包；模型/可检测和rank条件须逐项映射。|
|Güzey & Güzey, SMP&T152,103318,2026；[DOI](https://doi.org/10.1016/j.simpat.2026.103318)；FULLTEXT|传感器→中心方位测量，单受攻链路；中心预测轨迹及多传感器信息|Sec2.2/3：NIS/LLR、滞回、staleness及慢恢复trust；中心Trust-WLS/KF；Monte Carlo/消融，无本轮所需分布式恢复调度定理|C/A的工程组合先例。原文明确攻击结束后异常持续就保持低trust，不能把慢恢复自身当新意。|
|Soleymani et al., IEEE TAC68(6),2023；[DOI](https://doi.org/10.1109/TAC.2022.3194125)；FULLTEXT公开作者稿|无攻击；Gauss–Markov系统、独立高斯噪声、可靠且有成本/一拍延迟通信；sensor/controller各有因果信息集|作者稿pp5–7式(1)–(13)、Theorem1：全局最优VoI触发+确定性等价控制；VoI=即时信息收益−包成本+未来价值差|A/B使用信息价值、预算/收益调度必须面对。原文不是攻击后Yang网络，不代表直接覆盖；但标准Bellman/收益阈值本身不能算本项目新理论。|
|Han et al., IEEE TAC60(10),2015；[DOI](https://doi.org/10.1109/TAC.2015.2409905)；FULLTEXT作者稿|无攻击的远端状态估计；接收端知道发送/静默事件|随机指数触发使条件分布保持高斯，推导MMSE/协方差及通信率优化；作者稿SecII–V|D的“事件/静默携带信息”是旧工具。确定性SoD条件分布一般非高斯，不能套随机触发精确公式。|
|Lao & Li, IEEE TSIPN,2024；[DOI](https://doi.org/10.1109/TSIPN.2024.3375605)；ABSTRACT|分布式参数估计，事件触发间未传信息；具体权限待全文|完整摘要明确inter-event information retrieval、闭式优化解、整体收敛充分条件；未核式/定理号|D直接近邻，摘要足以否定“首次利用未发送信息”，不足以判断具体Replay能力或证明与本候选等价。|
|Gao, Yang & Chai, Automatica,2026；[DOI](https://doi.org/10.1016/j.automatica.2026.112837)；METADATA|题名为quality evaluation-based resilient distributed estimation，多跳时变网络；其精确攻击权限未核|无本地全文/完整摘要；不能填写算法/定理号|A直接排重前置未完成，不得宣称信息质量/价值加权尚无直接解。|
|Hu et al., Systems & Control Letters,2026；[DOI](https://doi.org/10.1016/j.sysconle.2026.106513)；METADATA|题名为measurement-weighted resilient filter，hybrid cyber attacks；具体字段/触发未知|无本地全文/摘要；“动态权重+事件触发”是用户提供待核描述，元数据尚不能确认其全部结构|A/C及普通动态加权的排重缺口，不能凭模型名称不同宣布新意。|
|Ye, Cao, Cai & Chow, Automatica,2025；[DOI](https://doi.org/10.1016/j.automatica.2025.112387)；METADATA+PARTIAL_ABSTRACT|差分隐私微电网分布式控制的False Noise Attack；噪声机制/攻击相关性待核|Semantic Scholar只有摘要末句，提到FNAD对三类攻击的理论检测效果；没有完整模型、算法/定理定位|F必须全文核读后再立项。不能把残缺摘要当作已完成“噪声伪装攻击”方法比较。|

## 2. Nasiri：B/C的实质直接竞争

**LITERATURE/FULLTEXT。** 原文不是“攻击结束后让trust恢复”。它在被判定不可信的agent上主动重构估计，使用当前/预测状态、本地观测、邻居加工观测以及共享状态构成批回归：

\[
o_i^{\rm batch}=M_i^{\rm batch}\theta_i+e_i^{\rm batch},\qquad
\min_{\theta_i}\sum_k w_{ik}^2\,\hbar(r_{ik}/(s_iw_{ik})).
\]

原文式(28)–(34)，PDFpp6–7；Cholesky白化为式(33)。trust决定观测权重，IRLS更新为式(38)。三层迭代分别更新状态、权重、邻居交换；式(44)–(46)是真实的通信与重构动作。PDFp9（正式p570）明确仅对异常agent/time激活以降低通信成本。因此“额外邻居通信用于攻击后状态恢复”已有直接方案。

其仿真实例用DC电网、单位状态转移（PDFp8/正式p569）；IEEE14/118bus、状态恢复曲线和迭代/计算代价在SecV。与LPE、集中恢复及R-ADMM等比较。不能因电网架构不同就忽略；公平适配必须给当前共同状态模型的共享状态/观测接口，计入这些消息与迭代。

**核查边界。** 未找到编号的主定理证明任意动态攻击后均方恢复，也未找到固定总字节预算内全局/近似最优的消息调度保证。这个“未找到”只约束本轮所读原文，不能提升为全领域未解决。PDFp8关于innovation covariance initialized to zero属于仿真初始设置，不能写成每次恢复都重置协方差的已证明规则。B只有在预算约束产生稳定、超过简单定频/随机发送的实际收益后，才可能建立窄问题增量。

## 3. Xu：主动重传和历史信息再利用已被做成完整算法

**LITERATURE/FULLTEXT。** 状态/协方差两类字段可被篡改，式(9)–(10)。实时检测器式(12)同时比较邻居状态/协方差；若拒绝，发送安全请求指示

\[
I_{k+1}^{ij}=\{i,j,k+1\},\qquad
T_{k+1}^j=\{j,k+1,\hat x_{k+1|k}^j,S_{k+1|k}^j\}.
\]

PDFpp5–6，式(13)–(17)。每个可疑消息只重传一次以限制开销；原文明确重传载荷也会受攻击，并非假定重新发送天然可信。另假设请求指示安全加密，sender能够保存并重传指定历史原始数据；这些是本项目不能默认拥有的资源。

式(18)在实时一致性项之外增加迟到历史贡献，示意为

\[
\bar\gamma_p^{ij}\varepsilon A^m
 (\check x^j_{p|p-1}-\hat x^i_{p|p-1}).
\]

不能把这个原式写成任意完整历史影响消除；它具体补回曾丢弃信息。Algorithm1/Proposition1给协方差上界及增益设计；Theorem1（PDFp9/正式p2860）在集体可观、连通、噪声及增益/协方差上下界等条件下给均方指数最终有界；原式引入通道攻击概率，Corollary1另讨论未知先验。时延窗口m关系见式(20)，并有相应延迟分析。实验为区域温度监测，额外重传/状态协方差开销需计。

**对B/C的限制。** 不能凭“我们使用Yang缓存，它使用预测包”宣称机制独有。若新方法也只发一个重传请求、重新检验、加上历史修正，基本已被它替代。潜在新增点只能是当前协议下已污染sender/缓存、总预算下选择何时刷新及可核查风险界；这仍需实验证实，不是已有成果。

## 4. del Nozal：C的重新信任/子空间协同不是空白

**LITERATURE/FULLTEXT。** Problem1明确要求重新接纳此前被攻击的agent。分布式multi-hop observability decomposition确定每个节点本地/邻居可估计子空间；根据分歧进入置信、警戒、不信任区域，修改对应信息权重。Def5（PDFp4）用

\[
\widetilde R_i=\{e:d_{Q_{i,j,\rho}}(e)<\widetilde r_{i,j,\rho}\},
\quad \widetilde r_{i,j,\rho}<a_{i,j,\rho}
\]

设置更严格re-trust区域，并重新运行setup以将信息源放回可观测分解；滞回用于避免频繁重算。Theorem1（PDFp5）对trust多胞体顶点给共同Lyapunov LMI，保证该切换族稳定。HIL比较见SecVI；“全权重范围稳定”依赖重新设计的observer，不能套给当前Yang固定名义增益。

因此C若只是“连续若干拍正常才重接入”“渐进放大权重”或“按可观方向保留信息”，缺少方法新意。真正待检问题是：网络状态已经受历史污染且信任证据相关时，什么**实际可算**的条件可限制重新接入造成的MSE损失；不能把正确攻击结束时刻或健康原始载荷默认给部署算法。

## 5. 残差交换、输入跟踪与UIO：可以继承什么

**Zhang & Yang：** local residual为\(z_i=y_i-H_i\hat x_i\)，通过正则化映射到共同状态空间，融合的是邻居残差而非邻居估计；原式(3)–(7)（PDFp3）。Theorem1的one-step optimality使用交叉协方差；Theorem2的有界性在明确的Assumption3统一Lyapunov条件下，且相应Sec3说明是正常、全接纳分析。Theorem3只对与当期正常残差独立的非零偏置证明统计量期望提高，Theorem4针对无法单独获知私有水印的反射攻击。不能把统计量期望增量升级成任意Replay的检测率保证。若本项目请求其他节点残差作为验证，必须与这一信息资源和融合基线比较。

**Deghat：** 作者稿p3 Remark将估计链路加性篡改写成observer输入，因此不能以“本项目是链路攻击、它是节点攻击”规避。Thm3的\(\hat x_i^c=\hat x_i+\hat e_i\)已是当前状态修正。它要交换额外检测器变量，以固定连续网络、admissible bias类、L2扰动设计LMI/H∞跟踪。项目之前P1未完成忠实离散性能复现；本轮仍不宣称已击败或已完全被其覆盖。

**Tabatabaei：** Theorem3.1在Assumptions2.1/3.2/3.3与Hurwitz条件下以级联UIO重构\(x_k,y_k,\Gamma_{ki}\)；Thm3.2把重构用于补偿。隐蔽类采用子空间拆分，Props4.2/4.3区分全/部分重构。原文可以恢复信号的rank/coupling信息在共同状态传感器网络中未必存在。可以继承UIO/重构设计工具；不能免费假设缺失的可辨识信息。

## 6. VoI与静默信息：D与B的标准部分

**Soleymani：LITERATURE/FULLTEXT。** 本轮唯一新下载为arXiv公开作者稿2103.14012。PDFpp5–7式(1)–(13)是有限时域Gauss–Markov系统、独立高斯初值/噪声、可靠有成本通信及一拍延迟；sensor/controller的信息集不同。Theorem1给

\[
\delta_k^*=\mathbf1\{\mathrm{VoI}_k\ge0\},\quad
\mathrm{VoI}_k=\tilde e_k^TA_k^T\Gamma_{k+1}A_k\tilde e_k-\theta_k+\varrho_k.
\]

证明使用dynamic programming、对称性与重排/majorization工具。这里\(\varrho_k\)是两种发送决定的未来价值差，不可随意删去后仍称全局最优。此文没有攻击污染Yang网络，却足以说明“按信息收益减成本触发”“预算/最优调度”是成熟竞争工具。攻击后B若仅重写Bellman方程或穷举一个有限预算，不构成新机制。

**Han：LITERATURE/FULLTEXT。** 已有随机触发的条件高斯、MMSE、协方差和通信优化，不传消息也提供事件条件信息；确定性SoD一般破坏条件高斯。不能把在SoD下使用Gaussian likelihood当成精确等式。**Lao：ABSTRACT。** 完整摘要明确把inter-event未传信息通过闭式优化恢复，给整体收敛条件；原始式/定理未读，不声称它已经/没有解决攻击问题。

**2026指定方向尚未完成全文排重。** 本轮精确检得 *Distributed state estimation with event-triggered measurement sampling*，NAHS2026，DOI10.1016/j.nahs.2026.101768；其是否利用静默或防Replay仍未核。另检得异步/二值/DoS题名，未因名称相近全部加入“已精读”池。对D的最初权限审计甚至可先于补全文：如果接收端不知道sender真实上次发送值，就不能直接计算合法SoD阈值；如果使用可伪造的载荷自报触发字段，也不能得到可信证据。一个能够匹配合法事件记录的历史Replay就是必须尝试的反例。

## 7. 本轮可作出的、不可作出的判断

1. **已建立：** B/C的主动恢复、历史重传、再信任有全文直接竞争。A的信息可观子空间/质量权重也不能视为空白。通信预算的动态规划、VoI及线性传播为标准工具。
2. **未建立：** 最近邻方法已经完整解决当前有限预算Yang污染恢复；同样未建立本项目有不可替代的新机制。必须先用有限预算oracle与定频/随机对照检验收益上限。
3. **未完成：** Gao/Hu/Ye及Lao的全文排重。特别是F不能在原论文攻击权限与噪声假设未核清时定题。下载入口见[最小缺口清单](sources/download_requests.md)。
4. **下载告知：** 新下载1份VoI公开作者PDF；Nasiri、Xu、del Nozal、Zhang&Yang等PDF均为用户已有附件。所有旧任务文件、原PDF及G3 plan未修改。来源与哈希见[source index](sources/source_index.json)。
