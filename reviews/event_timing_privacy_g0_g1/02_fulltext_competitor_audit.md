# G0：公式级竞争文献审查

证据标签：FULLTEXT=已取得并核对全文；PREPRINT FULLTEXT=已取得作者公开稿并阅读，不声称核了正式排版；OPEN=证据不足。来源页码、版本、DOI和哈希见sources/source_manifest.json。

## A. Mason et al.：时序侧信道已被正面研究

**PREPRINT FULLTEXT** Federico Mason, Federico Chiariotti, Pietro Talli, Andrea Zanella, “Secure Goal-Oriented Communication: Defending Against Eavesdropping Timing Attacks,” IEEE JSAC 44 (2026), 3782–3797, DOI 10.1109/JSAC.2026.3669875。已取得ArXiv:2507.14212作者稿13页；出版社/Padua库下载端本轮403，页码按预印本。关键位置：§III–V、式(3)–(16)、Theorem 2、Algorithms 1–2。

模型中发送者Alice知道Markov状态s(n)，接收控制者Bob按当前状态和距上次接收间隔决定拉取时刻；状态相关策略sigma(s,Delta)决定通信。Eve看不到内容，仅观察相邻请求间隔tau。式(8)–(11)使用forward/backward HMM递推推断状态；式(5)定义最近D步的归一化熵信息泄漏
L_E(n;D)=max_d[1-H(phi_E(n;d))/H0]。
因此“消息时序泄漏系统状态”以及“调度策略可抑制泄漏”已被直接研究。Theorem 2证明特定recurrent Markov估计情形的周期调度使长期泄漏达到先验下限；ADE/PDE两种启发式在通信收益与泄漏之间折衷。

差异：Mason的通信决策者合法地基于状态作调度，Eve被动观察；没有Eve向估计器入站链路注入值、改变受害Yang估计再改变受害者发送事件的闭环动作。候选在攻击动作对SoD事件的干预式和“攻击造成的增量泄漏”度量上不同。但这只是数学对象差异；不能宣称首次研究时序隐私。周期/策略熵防护也是必须对照的成熟思路。

## B. Crimson et al.：active eavesdropping不是FDI注入

**PREPRINT FULLTEXT** Matthew J. Crimson, Justin M. Kennedy, Daniel E. Quevedo, “Remote State Estimation with Privacy Against Active Eavesdroppers,” Automatica 171 (2025), 111932, DOI 10.1016/j.automatica.2024.111932。核读arXiv:2308.08790作者稿13页；正式出版式尚未核，全文是作者预印本。

§2.2–2.3定义传感器向remote user发包，legitimate user和Eve分别有Bernoulli packet reception indicators；攻击是在时刻Lambda开始jamming通信，改变合法接收率gamma到gamma-bar，同时Eve具有自己的packet reception率。主动目标是拦截包并降低合法用户估计、同时获取包。§4式(9)–(11)使用预共享伪随机indicator，在detect后让传感器随机发state或noise；Lemma 1及式(14)–(20)递推两方估计误差协方差，优化噪声发送概率mu。

该文的active是干扰/丢包信道，不是篡改输入估计并诱导受害者SoD时序。它没有定义受害者后续事件对私有本地量测的mutual information；但已覆盖active eavesdropper、remote estimation、窃听与系统估计性能的联合问题，故候选不能用宽泛表述声称首次连接主动攻击与隐私。

## C. Si et al.：事件触发DKF、隐私和篡改防御同文出现

**FULLTEXT** Kang Si, Peng Li, Zhi-Peng Yuan, “Secure and Privacy-Preserving Distributed Kalman Filtering for Sensor Networks With Event-Triggered Mechanism,” IEEE TIFS 20 (2025), 7438–7453, DOI 10.1109/TIFS.2025.3588670。16页出版社PDF全文。

式(7)–(14)，pp.7440–7441：引入动态mask状态r_i，触发函数
f_i(m)=||z_i(m)||−theta_i exp(−mu_i m)，其中z_i(m)=r_i(m_i,tau)−r_i(m)，以masked-state变化触发。与此同时，攻击者可窃听并篡改mask状态包，但接收端用Paillier加密hash签名验证；验证失败时式(15)将融合权重置零。Theorem 1–2，pp.7442–7443，分析mask下average consensus及trigger稳定/Zeno-exclusion；Theorem 4–5，约pp.7448–7449，讨论HBC/外部窃听者对本地初始状态的隐私。Remark 2，p.7443明确其privacy机制聚焦状态保护、signature防数据修改，同时指出remote measurement tampering不在本文考虑范围。

因此“event-triggered DKF + privacy + active data tampering”并非空白。差异是Si通过认证阻止受篡改报文进入一致性融合，未量化合法已接收的入站FDI如何对受害节点下一次SoD事件产生额外互信息；其触发量则是本节点mask状态，不是候选定义的Yang估计变化。这是部分覆盖与模型差异，不是空白证明。

## 对照结论

|问题|已有覆盖|候选可能不同的对象|判断|
|---|---|---|---|
|时间事件本身能否泄漏状态|Mason用状态相关调度、HMM后验和熵损失直接分析|攻击动作因果改变一个Yang SoD事件，量化增量互信息|时序侧信道问题已覆盖；干预子问题部分覆盖|
|主动窃听是否同时影响估计|Crimson研究窃听加jamming/packet drop及双方估计协方差|攻击者篡改入站估计值，经Yang递推改变下一事件|主动窃听广义场景覆盖；攻击机制不同|
|事件触发DKF中是否考虑篡改|Si同时有mask触发、窃听和篡改，但用signature拒绝未认证数据|不使用认证时，对已采用的入站FDI作因果互信息分析|相关架构已覆盖；候选定量对象未见等价式|
|候选是否已新颖/可立项|三篇均未找到完整相同定理|还需检索active event-trigger manipulation、covert timing channel和因果控制隐私|OPEN；NOT DIRECTLY COVERED不等于NOVEL|

## 来源与限制

Mason 以arXiv作者稿作为全文证据，正式JSAC卷期页码由Crossref核到，但出版社PDF未取得；若负责人要求正式版页码/定理核对，可再下载。Crimson 同样以作者预印本核对正式DOI对应工作。Si是指定的正式出版社全文。没有在本轮做大规模文献搜索。
