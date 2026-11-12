# FDI / Replay分布式估计：方法级全文精读

日期：2026-11-12。对象为邻居估计载荷的链路篡改、FDI和Replay。逐篇记录系统/攻击权限、具体方法、定理对象、实验与本项目含义。定位见sources/reading_locators.csv。文献转述不代表本轮独立证明原文全部定理。

证据标签：L=原文明确公式/假设/结果；M=从明示公式直接推导；E=本项目既有实测；H=待验证；U=未核完整。L不表示原论文全部数学均经本轮重新证明。

## 一、直接主干：随机激活、FDI空间盲区和保护器

### 1. Yang et al. 2014

W. Yang et al., “Stochastic sensor activation for distributed state estimation over a sensor network,” Automatica 50(8), 2070–2076, DOI 10.1016/j.automatica.2014.05.025。完整7页期刊PDF。正文pp.2071–72式(1)–(11)，Theorem 1及pp.2073之后LMI分析。

每个传感器以独立Bernoulli概率q激活；激活则更新本地量测并和邻居交换估计，不激活仍接收邻居。更新为

\[
\hat x_i^+=A\hat x_i+K_i^p[y_i-\gamma_iH_i\hat x_i]
-\epsilon A\sum_{j\in N_i}\gamma_j(\hat x_i-\hat x_j).
\]

证明必须维护节点间交叉协方差P_{i,j}：式(6)写误差乘积展开，式(7)推联合协方差，式(9)给在该协方差条件下的局部MSE最优增益。原Theorem 1及Lemma 7–9针对无攻击随机激活的稳态MSE上下界和稳定条件，要求随机系统stabilizability/exact observability等；不能移植为事件SoD缓存攻击下的稳定保证。

项目五节点是Yang-form研究模型，但将随机激活改成估计值Send-on-Delta、每步可得本地量测，并按收到估计缓存外推，且名义全通信增益复用。因此应标为改编，不是完整复现。性能/稳定定理须重新验证。

### 2. Yang et al. 2019

W. Yang et al., “Distributed filtering under false data injection attacks,” Automatica 102 (2019), 34–44, DOI 10.1016/j.automatica.2018.12.027。完整11页期刊文。

原估计器发送估计及innovation，独立随机阈值保护器在接收端对邻边残差做软拒绝。式(5)–(7)给随机保护与动态估计；式(8)–(10)为误差相关递推和最优gain，Theorem 3、6、7给攻击模型下Gaussian性/误差界/稳定性条件。Assumption 1图强连通、Assumption 2过程可控等，结果不是任意拓扑、任意攻击者的鲁棒界。

**细节约束。** p.37 Remark 2明确：包同时含estimate和innovation，但不区分字段；攻击者如果只改estimate并保留innovation，邻居检查创新会失效。2022进一步对状态包空间盲区给充要条件。评审时必须说明包字段和攻击权限，不能略掉这一先例。

### 3. Zhou et al. 2022

J. Zhou et al., “Security analysis and defense strategy of distributed filtering under false data injection attacks,” Automatica 138 (2022), 110151, DOI 10.1016/j.automatica.2021.110151。期刊PDF 9页。

邻居估计m_j被加z_ij；接收节点用本地量测构造windowed Chi-square残差统计。Theorem 1（pp.110151-3/4，式(10)–(15)）说明若rank(H_i)<n，可找非零Ξ使H_iΞ=0，接收空间检验仍保持正常，而共识误差被λAΞ驱动；这不是说所有攻击轨迹都能保持隐蔽，而是该统计量的状态零空间漏洞。Algorithm 1具体构造z_ij=Ξ−Δm_j。

随机保护器在每节点每步抽xi_i~Exp(1)，按估计差平方门控；式(24)接受概率为exp(−distance²/nu)。Theorem 2在明确谱条件下给安全定义，Theorem 3证明保护后的误差Gaussian。它优先维护稳定性与可分析性，不能把“secure”翻译成攻击零MSE或指定FPR的检测率。

**直接基准。** 必须在同攻击机会、同本地量测、同消息负载、同正常拒绝率下比较该随机保护器。若提出连续权重w=exp(−cJ)，条件单步均值与Zhou随机门控有关系；闭环不等价，但绝不能只跟无保护Yang比。

## 二、邻居估计载荷与Replay直接对手

### 4. Yu et al. 2025 SPL

Y. Yu et al., “Distributed Secure State Estimation Against Stealthy Attacks,” IEEE Signal Processing Letters 32 (2025), 1930–1934, DOI 10.1109/LSP.2025.3564886。完整5页，用户本轮新下载到Zotero。

式(2)–(3)是接收节点估计差二次检测。Lemma 1 / 式(4)：改包为m_j^a=2m_i−m_j，则m_i−m_j^a=−(m_i−m_j)，Chi-square统计精确不变；Theorem 1给受攻误差协方差不低于正常。该反射策略需要实时接收端估计/当前邻居估计的攻击权限，比本项目只重放以前截获的真实包更强，必须分开比较。

多邻居版本先排序，协调本节点估计两侧的边，使反射误差不互抵；Theorem 2比较节点协调攻击与单边攻击。防御是历史估计产生的动态编码矩阵，在估计上增加辅助分量、接收端按同步矩阵解码。Theorem 3对该编码与反射策略证明统计量随注入增大。它不是无钥状态时间戳，需编码矩阵同步，也不是被动间隔标定。

### 5. Huang et al. 2024 TCyb

Huang et al., “Security Analysis of Distributed Consensus Filtering Under Replay Attacks,” IEEE Transactions on Cybernetics 54(6) (2024), 3526–3539, DOI 10.1109/TCYB.2022.3209820。完整14页。

攻击者记录所有sensor measurement一个长度tau片段，然后在攻击区间循环发y_i(k−tau)；可选传感器子集。不是邻居估计payload Replay。Theorem 1–7分稳定/不稳定系统推误差协方差与残差KLD；Chi-square/残差统计分析攻击隐蔽性。攻击起始时记录状态与当前靠近会降低瞬态可检测性；稳定系统误差有界不等于攻击无损。论文提及跨传感器旧量测重放是未来更复杂场景，说明不应声称单边/跨边迁移已经得到原文覆盖。

### 6. Su et al. 2022 IEEE Systems Journal

L. Su et al., “Distributed Secure State Estimation for Cyber-Physical Systems Against Replay Attacks via Multisensor Method,” 16(4), 5720–5728, DOI 10.1109/JSYST.2021.3123617。完整9页。

记录/重放多传感器测量片段，识别依赖包标记/标签来源与接收的区别，再隔离受攻sensor并以安全sensor构造observer；Theorem 1给observer稳定充分条件。Remark 2明确攻击者只能录数据，不能识别packet category并篡改其label，因此100%检测结论不适用于无可信新鲜度字段、当前包内容可替换的设定。本课题没有该标签安全假设，必须在比较表写清。

### 7. Xing et al. 2025 TIFS

J. Xing et al., “Stealthy Attacks With Historical Data on Distributed State Estimation,” IEEE TIFS 20 (2025), 4541–4550, DOI 10.1109/TIFS.2025.3564063。用户本轮新放入Zotero，共10页。

智能传感器对consensus Kalman发创新z_i,k。攻击先窃听/存τ时间创新，再混合延迟及当前创新：
\[
z^a_{i,k}=T_{i,k}z_{i,k-\tau}+L_{i,k}z_{i,k}+b_{i,k}.
\]
式(8)对长度barτ窗口做Chi-square energy，完全隐蔽条件(9)用创新协方差匹配；不等价于整条观测记录同分布的最强隐蔽定义。Lemma 3、Theorem 1推受攻网络误差covariance；在当前/历史创新组合约束下每时刻攻击优化可写convex SDP，拓扑block-diagonal限制使covariance relaxation可能不可达；Theorem 2给次优piecewise-constant攻击策略。

该攻击能选择/线性组合观测，但输出字段是innovation，不是只能选一条过去邻居estimate包。它已经覆盖历史驱动、KLD/统计隐蔽和拓扑攻击优化，不允许声称“历史攻击对状态估计无人研究”。

### 8. Ge et al. 2026 TCyb

C. Ge et al., “Optimal Stealthy Attack Design for Distributed Consensus State Estimation: A Historical Innovation-Based Approach,” IEEE TCyb, 1–13 (2026), DOI 10.1109/TCYB.2026.3721072。完整13页。

分布式Kalman滤波创新包攻击；全模型/拓扑知识，历史innovation攻击矩阵block diagonal。历史影响通过时序协方差递推，χ²检测的多步统计和KL约束定义隐蔽，Theorem 1 attacked covariance recursion、Theorem 2 relaxation benchmark，基于PGD计算满足图拓扑限制的攻击矩阵。证明对象是创新边统计/KL和估计误差，不是接收端在不看私有y时选历史状态包。

### 9. Wen & Wang 2018 DSP

F. Wen & Z. Wang, “Distributed Kalman filtering for robust state estimation over wireless sensor networks under malicious cyber attacks,” DSP 78 (2018), 92–97, DOI 10.1016/j.dsp.2018.03.002。

每节点收neighbors的estimate与covariance，对状态及协方差对角分别K-means聚两簇；trusted cluster可用多数票，也可借secured-node标识。可信簇内均匀平均估计及协方差，Alg.1。仿真9节点全连通，2 secured、5 compromised，随机/FDI/Replay。

信任聚类、空间一致性、动态融合已出现；其安全节点版本额外使用trusted node，局部邻居多数规则需逐节点核对，不能只看全网半数。两种算法通信含covariance，不能和只发estimate的方案只按一向量计。

## 三、紧邻信任、残差、时序参考与饱和方法

### 10. Liang & Wang 2019

“Trust-based distributed Kalman filtering for target tracking under malicious cyber attacks,” Information Fusion 46 (2019), 44–50, DOI 10.1016/j.inffus.2018.04.002。本地来源为Chalmers作者稿，PDF第1页是仓储封面，论文从PDF第2页开始。

正文PDF第9–13页、式(8)–(18)、Algorithm 1：交换各节点estimate与covariance；每节点本地执行两簇K-means状态与协方差聚类，最大簇作为trusted set；对trusted estimates及covariances分别均匀加权，再做diffusion Kalman。模型假设少于半数节点受攻，仿真有random/FDI/Replay。它足以否定“trust-weighted distributed Kalman first”。筛选时须显式标注其节点攻击/多数节点可信假设与本项目单边载荷篡改权限不同；不能在比较表里只数一个M维状态包。

### 11. Zhang et al. 2024 Electronics Letters

Z. Zhang et al., “Temporal convex combination-based secure distributed estimation against cyberattacks and noisy input,” 60(6), DOI 10.1049/ell2.13156。对象是未知参数向量diffusion RLS，不是动态状态缓存滤波。节点同时发cooperative intermediate estimate和non-cooperative estimate；邻居将non-cooperative的当前分量排序取中值作spatial reference，再与历史reference按convex factor混合，广义correntropy在线更新组合因子，阈值检验neighbor estimate。

FDI包括fixed、time-sharing、discontinuous，处理regression input noise。训练比较为dRLS/BCRLS/secure BCRLS/TCS/TACS，50 Monte Carlo。公式(10)统计/阈值参考用邻居分布，但没有真实接收间隔Δ条件标定。其两种估计向量通信、参数静态，与本项目状态包模型不同；“时空参考”仍非新口号。

### 12. Peng et al. 2025 IEEE Sensors Journal

S. Peng et al., “Robust Secure Distributed Estimation Based on Statistical–Temporal Fusion Over Adversarial Sensor Networks Against Noisy Interference,” 25(15), 29966–29981, DOI 10.1109/JSEN.2025.3581080，全文16页。

对象也是未知参数diffusion BCMCC，ANNI-II输入噪声与impulsive interference，节点攻击估计值。接收邻居noncooperative estimates，逐参数sort取median当前spatial reference，再做
\[
\bar w_{k,i}^{(m)}=\epsilon\bar w_{k,i-1}^{(m)}+(1-\epsilon)\dot w_{k,i}^{(m)}.
\]
空间偏差控制权重，temporal smoothed reference，再以statistical feature ensemble自适应generalized correntropy kernel width/combination，阈值检测并融合。算法间每节点/链路每轮发M scalars。含fixed/time-sharing/discontinuous FDI和input noise，比较多种扩散估计，Monte Carlo 50次。

直接挑战“时间参考+统计阈值+权重”为新；但与状态滤波不同，时间下标i为RLS参数估计迭代，不等于一次缓存驻留物理step或不规则成功接收间隔Δ。

### 13. Güzey & Güzey 2026 SMP&T

完整15页，doi 10.1016/j.simpat.2026.103318。SISMF节点bearing送central fusion center。NIS、χ²/scale-χ² likelihood，leaky log-odds、logistic trust、severe gate、hysteresis recovery、WLS/IRLS robust geometric fusion、Kalman pseudo-measurement adaptive R。攻击limited nodes切换、dwell time；Replay为hold-last stale bearing。Theorem 3.1/3.2仅在攻击/诚实NIS可分、geometry richness、dwell time成立时保证trust分离与有限lag后的bounded tracking。50 Monte Carlo、ablation、P/R指标及runtime。

历史likelihood trust及恢复并非新；中心bearing architecture不是Yang逐节点全状态估计包。同权限无法直接排名，但需要比较其对本课题最接近的创新残差/时间强度基准，说明架构差异。

### 14. Zhang & Yang 2026 JFI

“Distributed secure state estimation ... residual-exchanging approach under FDI attacks,” 363:108914, DOI 10.1016/j.jfranklin.2026.108914。发送local residual、用regularized map到状态空间、windowed χ²检测、邻居残差fusion。Theorem 3对不能实时取残差的独立bias证明非零bias提高期望统计；Theorem 4给real-time residual attacker下private Gaussian watermark对reflection attack的能力。Theorem 2 mean-square bounded要closed-loop Lyapunov条件。

创新包换成residual可能改带宽和检测信息，故不能只把残差版等同于“不公平增加通信”；应计实际字节。水印版需共享秘密权限，须与纯被动算法分组比较。

### 15. Wang et al. 2026 TASE

“Secure State Estimation Against Sparse Sensor Attacks: A Distributed Adaptive Saturation Method,” 23:2091–2099, doi 10.1109/TASE.2025.3649048。稀疏sensor measurement attack、bounded noise、local unobservable；每node堆叠n步输出做O_i，按\(\beta=\min(1,\gamma/\|Y_i-O_i\hat x_i\|)\)饱和本地innovation，再consensus梯度。γ随algorithm iteration \(k\)增长；这里iteration不必等于物理采样时间，需核查。Assumption 3 2s-sparse observable，Theorem 1一致，Theorem 2有界误差，time-varying攻击扩展Theorem 4。

饱和对攻击有用但并非独立新点；它不等价于在单条邻居状态差clip。局部观测和全网稀疏冗余非常关键，不能直接声称此理论涵盖五节点基准。

## 四、序贯证据、AoI与恢复

### 16. Tunga et al. 2018 ACC

windowed chi-square与staticχ²、CUSUM比较。给足够攻击信号/最坏steady-state deviation下零报警误差上界、按Gamma分布设置目标false alarm阈值；window overlap相关性和随机游走协方差在其模型下推。它不覆盖网络estimate缓存，但累计平方差不是当前candidate独创。

### 17. Qiu et al. 2019 TIE

triggered transmission error通过ZOH误差界加入fault detection residual；H∞/LMI优化residual generator和time-varying threshold。是event-triggered阈值按通信误差变化的直接邻近，但对象plant fault、单残差生成器，不是通信包完整性。

### 18. Liang–Liu 2023 TIM

event-triggered连续MAS，邻居数据ZOH保持，UIO估本地邻居并产生adjacent residual检测攻击/故障；触发通信误差显式出现在检测的H∞鲁棒性—敏感度优化中。攻击可连续改保持信号，非仅新包上一次载荷替换。本地模型是physical coupling agent，不是多传感器共同观测同一x。

### 19. Mitra et al. 2022 TAC AoI

时间变通信图下distributed observer，用freshness index追踪数据来源年龄和多跳传播；state由来源节点估值按A推进。Byzantine扩展中允许对方撒谎freshness，使用多邻居quorum/trimming与拓扑强鲁棒性；不把age tag当可信事实。模型/图条件比本项目丰富很多，也说明缓存外推/年龄抑制的贡献密度高。

### 20. Berman 2014，Kalman outlier rejection

multipath measurement例子展示innovation gate可能拒绝有效样本，讨论单边gate/multifilter初始化等恢复策略。攻击前一包导致后续时差分误罚已是已知现象，不应把一个reset heuristic独立当新算法。

## 五、结构与理论边界：不能把攻击者假设偷换

### 21. Pasqualetti et al. 2013

TAC 58(11):2715–2729, doi 10.1109/TAC.2013.2266831。descriptor/LTI未知输入系统的static/dynamic/active monitor，攻击零动态和不变零条件刻画不可检测。攻击者全状态/模型且连续任意输入，结果是轨迹兼容几何，不是随机网络包下有限统计检验。

### 22. Fawzi et al. 2014

TAC 59(6):1454–1467, doi 10.1109/TAC.2014.2303233。secure estimation/control下sparse sensor error及错误可纠正条件，信息/编码约束。用于解释观测冗余，不是当前攻击检测器。

### 23. Nozal 2022与Chen/Kar/Moura 2019

Nozal为多跳可观测子空间级信任；CKM为s-sparse sensor错误有限时域可唯一解码条件。两者都要求观测/拓扑结构冗余，不能靠更多历史样本消除\(\ker H_i\)中的一致攻击。

### 24. Event-triggered相关

Qian 2023的Gaussian truncation、Qiu 2019的trigger-error threshold、Solowjow 2018的inter-event学习都说明触发机制会选择样本。任何正常标定必须和同一触发协议、闭环样本分布匹配；这些统计步骤不是网络安全新发明。

## 六、审计附带的小型解析检查

代码mechanism_checks.py可按case独立执行，不包含Monte Carlo训练/性能提升宣称。

- Yu反射：固定一个二维SPD precision后验证反射前后当前状态差二次量精确相等。这里不能增加本地量测证据作为双方等价检查。
- Replay时间残差分解：
\[
r^{rep}_r=m(s_r)-A^{\Delta_r}m(s_{r-1})
=\underbrace{m(s_r)-A^{\delta_r}m(s_{r-1})}_{history\ residual}
+(A^{\delta_r}-A^{\Delta_r})m(s_{r-1}).
\]
\(\delta_r=\Delta_r\)时错配项为零；所以不规则到达间隔本身不保证顺序片段Replay的时间残差异常。
- 动态一致bias：若接收间隔内b_r=A^{\Delta_r}b_{r-1}，时间差分不增加攻击贡献；但攻击切入/退出边界、空间量测等可能揭示它。是已知模型推论，非普遍隐身定理。
- 窗口相关：单步各自N(0,1)但\(z^a_t=(z_t+z_{t-1})/\sqrt2\)使lag-1相关.5。按nominal iid χ²₂的5%阈值扫长度2，数值窗口false-alarm约5.95%，说明单步marginal校准不等同滑窗risk校准。
- 共享缓存误差：toy \(A=C=1,Q=0\)，r_a=b+e_cache+mean(v_{0:a})。前缀均值方差为\(\sigma^2_{cache}+\sigma^2_v/L\)，共享旧包不确定性不会随新测量样本平均到零；可见差异来自共同随机截距，不是新统计理论。
- Matrix顺序反例：即使A−B⪰0，也不一定APAᵀ−BPBᵀ⪰0（矩阵不交换）。原文Lyapunov递推若对不稳定A或交叉项直接作该比较须逐条件核查。此例只针对这个普遍代数推论，不单凭它判原文 theorem false。
- leaky LLR：\(\ell_k=\lambda\ell_{k-1}+c\)的期望极限为\(c/(1-\lambda)\)而非发散；若文献只以mean drift声称trust一定收敛到0/1，还需随机过程强收敛或不同更新机制。这是核查提醒，非对Güzey定理定罪。
- Gaussian complement：触发概率按quadratic指数时，给定收到载荷残差的选择分布一般是两个Gaussian密度之差，不是单Gaussian。Qian打印矩公式也有本地审计问题，已分开归档，未用于方向推荐。

数值诊断/来源程序输出见[evidence/mechanism_checks_v3](evidence/mechanism_checks_v3)，精确误差只是浮点积分误差，不作形式区间证明。

## 七、只围绕原问题的贡献边界

不建议把“Space + time + history + trust + cap”逐个模块列创新。现有工作分别已有可信聚类、空间Chi-square、随机软保护、时间记忆、AoI、窗口χ²/CUSUM、恢复门控、稀疏攻击饱和和残差交换。

若继续写增量型学报论文，必须先把一个可证伪的小问题固定，并从信息差异说明前人为什么不能直接给出该结论。当前最值得先筛的是**缓存驻留episode中共享估计误差带来的持续FDI检验问题**，因为它与原工程和已完成长episode证据直接相连；历史包字典选择型Replay应作为同一筛选中的攻击强度/隐蔽性压力，不单独宣称防御贡献。两项都尚未过独立新颖性门槛。详见problem_selection.md。
