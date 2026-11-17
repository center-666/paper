# ACK-V1 P5：直接竞争文献矩阵

截至2026-11-17；基准 e31e2f1c141bc67788149a4e0ca8f334c34e92ef。统一记历史阻断 H_k、未来历史占用 U_k(t)、滑窗长度 L、预算 B、截止 D、全失败分支的尝试集合 S。来源版本、SHA256及入口见[13来源清单](13_p5_source_manifest.md)；逐项映射见[11](11_p5_theorem_equivalence_audit.md)。

**判定口径。** EQUIVALENT＝明确共同条件下数学等价；SPECIAL CASE＝原文被当前结果覆盖；COROLLARY＝由列出的既有定义/结果直接推导，不等于原文已写出；ANALOGOUS＝对象相似但不能直接推出；NOT COVERED限于所核全文，不等于全领域不存在；OPEN＝无法取得正文或无法判断。

## 滑窗擦除与编码

| 文献及读取状态 | 模型、约束及原文定位 | 与T1/T2/T3的关系 |
|---|---|---|
| Badr等2013, ISIT, DOI 10.1109/ISIT.2013.6620377 | 16页arXiv:1305.3596v1作者稿；PDF2 §II定义 C(N,B,K,W)：一窗内一次长度≤B突发加≤K孤立，或≤N任意擦除；PDF3 Lemma1、PDF4 Thm1式(10)为码恢复/码率界 | K=0,N=B时窗口模式恰为最多B个任意擦除；**T1 COROLLARY**，不是论文显式提出ACK定理。T2/T3 **NOT COVERED（所核文本）**；对象是编码恢复 |
| Badr等2017, TIT, DOI 10.1109/TIT.2016.2618924 | Zotero QM8GAQDM，32页全文；PDF2 §II定义 C(N,B,W)，PDF3 Definition1、Thm1–2式(1)(2)为有限延迟T及码率R界 | N=B子类映射硬滑窗；**T1 COROLLARY**。ACK历史和首成功成本不在所核定理，T2/T3 **NOT COVERED（所核）** |
| Krishnan–Kumar2018, ISIT, DOI 10.1109/ISIT.2018.8437570 | 17页arXiv:1801.05919v1；PDF1–3定义 C(N,B,W)、有效延迟 T_eff=min(T,W−1)，式(1)为码率上界 | N=B子类同上，**T1 COROLLARY**；T2/T3 **NOT COVERED（所核）**。不混淆信道模型中的N与B |
| Krishnan–Shukla–Kumar2020, TIT, DOI 10.1109/TIT.2020.2983152 | 50页arXiv:1903.06210作者稿；PDF1–3定义任意≤a擦除或≤b突发、截止恢复；PDF2讨论ARQ与FEC | a=b=B、w=L时得总数约束；**T1 COROLLARY**。流码率构造不等于ACK首成功成本。2018和2020为不同题名/作者版本 |
| Dey等2025, ISIT, DOI 10.1109/ISIT63088.2025.11195616 | 6页arXiv:2504.19773v1；PDF2式(2)–(5)为AVC误码/容量，PDF3 Thm1–2为增长窗口、随机编码及oblivious jammer | 局部约束思路 **ANALOGOUS**；T1–T3逐式蕴含关系 **OPEN**，不能由滑窗字样认定等价 |

**T1映射。** 在Badr2017的 N=B 子类，将发送失败设为擦除序列 e_t=1{t∈H_k∪S}。全部S尝试失败合法，当且仅当每个物理窗口擦除数≤B。因H已合法且未来不发送不计入有效阻断，检查k…D即得到 U_k(t)+N_S(t)≤B；取补集便得T1。需要单独补上ACK的全失败分支与因果在线守卫，不能称Badr原文显式写了这个定理，也不能把编码解码等同于收到一个原始包。

## ACK、最大连续丢包与DoS控制

| 文献及阅读状态 | 信息、动作和定位 | 与T1/T2/T3 |
|---|---|---|
| Dolk–Heemels2015, DOI 10.1109/EBCCSP.2015.7300651 | Zotero IBRUV6HN，7页；PDF2 Standing Assumption1限制成功以来连续失败 δ≤δ_max；PDF3式(6)–(8)、PDF5 Thm1给ACK动态触发、最小事件间隔和 Lp 性能 | ACK与重试已有；**ANALOGOUS**。所核定理不是已知H_k的单截止次数前沿 |
| Dolk–Heemels2017, Automatica, DOI 10.1016/j.automatica.2017.02.029 | Zotero D3NPPM4W，13页；PDF3–5状态(y,e,τ,δ)、式(7)–(10)、跳变(15)(16)；PDF6 Condition2式(26)、Thm1；PDF8 Thm2无ACK | MANSD限制连续尝试失败；与物理时隙滑窗不等价；**ANALOGOUS** |
| Dolk等2017, TCNS, DOI 10.1109/TCNS.2016.2613445 | Zotero T7RVEXKU，14页作者版；PDF4式(5)–(7)依反馈切换；PDF6式(18)(19)限制DoS频率/时长；PDF7–8 Thm2式(31)–(36)为稳定和L∞性能 | **ANALOGOUS**：连续时间DoS频率/时长不同于逐拍有效阻断硬预算 |
| Dolk2017博士论文 Resource-aware and resilient control: with applications to cooperative driving | TU/e记录已确认；第5章全文未取得 | T1/T2/T3 **OPEN**；不得称其未覆盖 |
| Sun–Peng–Shen2024, DOI 10.1109/TICPS.2024.3419057 | Zotero 9LSU8AKD，9页；PDF4式(6)(7)(9)(10)依据ACK历史切换阈值；PDF6 Thm2式(26)：σ_m≤(1+σ_M)^(1/(M+1))−1，保证其条件下UGAS | **ANALOGOUS**：连续丢包数与阈值/稳定性已有定量关系；M不是本项目滑窗预算B，不直接给T2/T3 |

**两约束不等价。** L=2,B=1，只在1、3、5拍尝试，滑窗内每次都可阻断，连续失败尝试数可任意长，因此硬滑窗不蕴含有限MANSD。反之，交替失败/成功的尝试串MANSD=1，但较长物理窗口可能包含多次阻断，不满足B=1。只有连续每拍尝试时，局部连续失败长度才受B限制。

## ACK调度与DoS博弈

| 文献及阅读状态 | 模型、信息和定理 | 关系 |
|---|---|---|
| Ding–Ren–Shi2016, DOI 10.1016/j.ifacol.2016.10.391 | Zotero GRT7AAVF正式6页；PDF3式(4)(5) SINR/PER与发送概率、式(6) ACK异或翻转、式(11)成功年龄；PDF4 Problem2式(14)长期平均能量，PDF4–5 Thm4式(21)–(23) | **ANALOGOUS**：文章声明其策略类内最优，目标是平均协方差/传感器能量、概率信道和ACK欺骗；不是硬滑窗逐路径首成功。式(21)与算例存在既有数值一致性疑点，不能借此否定文章全部结论 |
| Han等2014, TAC, DOI 10.1109/TAC.2013.2294820 | Zotero KKG63376，6页；PDF2 Problem2.1长期平均期望协方差/能量；PDF3在线ACK方案式(9)、Thm4.3；PDF5 Thm4.5、Thm5.3 | **ANALOGOUS**：ACK在线调功率已有；长期平均能量不等于物理滑窗最坏首成功 |
| Ding等2017, Automatica, DOI 10.1016/j.automatica.2016.12.020 | 正式8页；PDF4式(9)–(12)到达概率、误差/能量奖励、无限折扣收益；PDF5 Problems4.3–4.4、PDF6式(15)(16) Nash值 | 有策略集合上的随机博弈优化；多信道折扣期望回报不同于单链路逐路径T2，**ANALOGOUS** |
| Ding等2020, Automatica, DOI 10.1016/j.automatica.2019.108680 | 本地11页作者机构稿；PDF4式(5) ACK异或、(6)(7)协方差/年龄；PDF6式(9)(10) belief转移；PDF3记Thm3.2平稳策略存在 | 功率/防御欺骗、reactive jammer，**ANALOGOUS**，不是可信ACK硬预算首成功 |
| Ding等2019, TCNS, DOI 10.1109/TCNS.2018.2867157 | QUT 15页作者稿；PDF4式(5)(6) SINR和到达概率，ACK对攻击方隐藏；PDF6式(13)–(15)误差/能量收益，PDF7式(16)无限折扣博弈，PDF8 Thm1静态均衡、PDF10 Thm3平稳均衡存在 | **ANALOGOUS**：信息不对称ACK博弈与T2不同，不能据题名认等价 |

## 2025–2026 新文献

| 文献 | 已核来源和内容 | 分类 |
|---|---|---|
| Lu–Lin–Yang2026, DOI 10.62762/CJIF.2025.922221 | 出版者所谓PDF返回34页网页打印件，只有摘要/引文、缺正文公式；摘要描述滑窗预测发送成功概率与Fisher信息排序 | 滑窗**概率预测**近邻；T1–T3 **OPEN** |
| Lv等2026, DOI 10.1016/j.automatica.2026.113214 | Zotero 3F45IBBK，12页；PDF4式(3)概率擦除、(4)(5)无限期平均收益；PDF5 Thm1式(6)(7)确定性平稳Markov策略、Thm2阈值结构 | 攻击者端平均收益最优调度；与逐路径截止minimax **ANALOGOUS** |
| Sun等2026, DOI 10.1109/TAC.2026.3706001 | Zotero E4GPKSXP，16页accepted manuscript；PDF3网络/ACK，PDF6 Thm1式(20)(21)稳定条件；PDF8 Thm2式(37)平均成本Bellman，PDF9 Thm3切换结构 | 多传感器冲突图/随机到达与无限平均MSE；ACK直接近邻，T2/T3 **NOT COVERED（所核）**；作者稿可能修改 |
| Hashemi–Maity2026, DOI 10.1016/j.ejcon.2026.101612 | Zotero 7UWLSKAU，9页期刊在线稿；PDF2式(2)(3) i.i.d.擦除和信息集；PDF3式(12)–(16)有限时域期望LQG+发送惩罚；PDF4 Thm1一步椭球证书；PDF5 Thm2 | 有限时域调度/发送成本 **ANALOGOUS**，信道概率而非硬滑窗；调度器有ACK历史、控制器基线不直接观测结果。arXiv:2604.06060同作者预印本题名/公式编号不同，以期刊稿为准 |

**剩余缺口。** Dolk博士论文第5章和Lu2026正式正文尚缺；完整来源见13。Ding2016等已收到Zotero附件并核对，不需重复下载。