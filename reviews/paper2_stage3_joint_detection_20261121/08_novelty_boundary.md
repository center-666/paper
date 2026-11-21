# 阶段3本地近邻公式级定位与创新边界

日期：2026-11-21。范围仅为已有本地全文、全文审查与保存题录。本轮复核了若干本地全文相关段落，并复用注明位置的既有全文审计；没有网络检索、没有新取得全文、没有对外消息，也没有改实验。

**判断：当前路线有工程原型价值，但大部分构件是已有序贯检测与事件选择模型的具体化。** 不能把联合似然、未知起点混合、O(J)递推或 \(b^{-2}\) 局部检测尺度分别包装成新算法原理。当前较值得继续核验的窄增量，是发送选择与发送后攻击共同决定的联合核，如何支持低开销warm候选、可证明的失配代价和与强选后创新基线相比的实际收益。全球新颖性仍为OPEN。

## 1. 本轮证据等级与可复查来源

|证据|本轮实际使用的材料|定位与限制|
|---|---|---|
|Han等2015|既有31页作者稿TXT相关证明段落；已有全文审计|[novelty_audit.md §2](../novelty_audit.md)，作者稿pp.6–12、式(8)–(10)、Theorem2式(22)–(26)；本轮不是重读全部31页|
|Shang–Yu–Chen2022|既有TAC正式全文TXT，CGC定义与Theorem1证明段落|[P6.1审计](../paper1_p61_theorem_literature_audit/01_shang2022_CGC_and_record_comparison.md)，pp.2053–2055，式(17)、(28)–(39)|
|Gupta等2026 QUICKDET|Zotero已有正文缓存，尤其式(15)/(16)与§4.5；已有完整正文审计|[QUICKDET全文审计 §2](../g1r_risk_constrained_recovery/05_quickdet_palmdkf_fulltext_audit.md)，[PDF版本索引](../g1r_risk_constrained_recovery/sources/fulltext_20261114/source_index.json)；补充S1/S2不在已有正文|
|Naha等2023|本地既有出版社全文TXT，§3.3–3.5、§4.1相关公式|本轮复核式(23)–(40)、Theorem1及Theorem2定位；没有完整独立重证原文全部最优性条件|
|Shen等2025、Li–Hu–Guo2025/2026|已有出版社全文公式审计|[JFI/Ad Hoc比较](../paper1_quantized_literature_fulltext_audit/02_jfi_adhoc_comparison.md)，[IJRNC审计](../paper1_quantized_literature_fulltext_audit/04_li_hu_guo_wiley_equation_audit.md)；本轮复用报告，不声称重新逐页阅读PDF|
|Wang等JAS2025量化水印|已有官方HTML全文审计|[JAS全文审计 §1](../paper1_quantized_cd_theorems_20261120/03_novelty_and_jas_fulltext_audit.md)；本轮不新增抓取|
|Guo等随机编码|旧研究包保存的题录线索|[后置相位报告“创新边界”](../paper1_postcommit_phase_defense_20261121/04_experiment_results_and_decision.md)；本轮未找到其可核公式全文，不给定理覆盖结论|

Han正确DOI为 **10.1109/TAC.2015.2406975**。旧G4表中出现的2409905与本地更完整的书目/全文审计不一致，本报告采用已核的2406975，不继续传播旧错号。

本轮直接读取的本地文本证据：

- Gupta：C:/Users/zhongxin/Zotero/storage/IBK4U734/.zotero-ft-cache，SHA256 001bd26604d62793d164fbddfa823c041ca117e6753e0f992f84adf7bd8dd8f6。
- 下面三份位于 C:/Users/zhongxin/shixidoc/mypaper/第二篇小论文/第二篇小论文/韧性恢复/references/：broad_topic_review_20261009/communication_security/Han2015_StochasticSchedule.txt，SHA256 ddaff20308e6c62f9989f78895c52ec86410948da3e845c87a4ffb1514b3e365；trigger_fulltext_review_20261010/Shang2022_WorstCase.txt，SHA256 a0e64b4a1dfe49ff9b5a2f8aacbc8b5ce97f2145186a866146363d03f5ef594d；direction_review_20261006/Naha2023_EJC_Quickest_watermarking.txt，SHA256 4d905daf8b7a7dcdfdffdef153c4b6e18147ee404c8cee2923f80103ea87e784。

第三方全文留在原位置，不在本包复制或上传。

## 2. 事件选择核：已有基础很直接

Han et al., *Stochastic Event-Triggered Sensor Schedule for Remote State Estimation*, IEEE TAC60(10):2661–2675，2015，DOI 10.1109/TAC.2015.2406975。

其指数二次随机触发、健康条件高斯更新、静默似然乘高斯后配方、发送给定真实量测后选择因子消去，都是当前估计器与核推导的直接基础。已有作者稿Theorem1证明在发送分支明确写
\[
f(x_k\mid\gamma_k=1,y_k,I_{k-1})
=f(x_k\mid y_k,I_{k-1}),
\]
理由是给定 \(y_k\) 后事件条件因子在Bayes分子分母抵消。当前不是首次利用发送/静默的条件信息。

Shang, Yu and Chen, *Worst-Case Stealthy Attacks on Stochastic Event-Based State Estimation*, IEEE TAC67(4):2052–2059，2022，DOI 10.1109/TAC.2021.3071948。其Definition1式(17)、Theorem1式(28)–(39)明确给发送后创新的CGC分布与事件概率。健康中心 \(r=0\) 时，
\[
\frac{\phi_S(u)(1-e^{-Zu^2/2})}{1-(1+ZS)^{-1/2}}
\]
就是该文标量CGC条件密度。旧库已经做过这个严格等价映射，不应在阶段3把它重新命名为“新的非高斯发送密度”。

当前扩展为已知量化残差 \(r\)、预测偏差 \(d\)，再在发送后加 \(b\)：
\[
f_{d,b}(u)=\phi_S(u-b-d)h(u-b-r).
\]
这一步是先乘已知选择概率、再做可逆平移的直接推前分布。\(h(u-b-r)\)对时序建模非常重要，错用 \(h(u-r)\)会导致检测器不正确；但**“写出正确核”本身通常属于必要的模型具体化，不是新的概率原理**。

可以保留的差别是：Shang的原源端滤波中心不被远端载荷污染回写，且原攻击权限还包括改变接收事件；本项目的实际反馈使 \(d\) 在未来递推，并限制攻击在可信事件以后。但这只能证明旧定理没有原封不动覆盖当前完整协议，不能自动推出方法创新。

## 3. QUICKDET是持续攻击检测的直接强近邻

Gupta, Baba, Sikdar and Chattopadhyay, *Quickest Bayesian and non-Bayesian detection of false data injection attack in remote state estimation*, Signal Processing244 (2026),110516，DOI **10.1016/j.sigpro.2026.110516**。

该文研究未知起始时刻后的持续FDI，主模型为传感器创新线性变换加独立高斯攻击噪声，后扩展到有限攻击模型字典。它不只是对每拍创新加一个阈值：

|正文位置|已存在的机制|对当前表述的限制|
|---|---|---|
|p.3式(5)–(8)、§3.2|给定起点/攻击模型的条件KF和攻击后相关创新条件分布|不能声称首次跟踪攻击后条件分布，或把对方当成只用独立健康创新的弱基线|
|p.4式(15)/(16)|攻击后条件密度对所有候选起点作后验混合；正文明确每个起点需独立条件KF|未知起点、多解释和混合似然已是直接先例|
|pp.5–6式(19)–(22)|有限攻击模型T的后验、ML/MAP识别|未知强度/模型候选库不是新概念|
|p.5Theorem3、§4.5|历史依赖最优阈值；QUICKDET/QUICKGRAD限制到常阈值并离线求参|本项目可比较显式校准开销，但不能称已胜过原文最优策略|
|p.6式(23)–(29)|非Bayes条件G-CUSUM、window-limited GLR及渐近延迟/FAR框架|持续FDI的序贯检测与延迟分析已存在，需作真正方法对照|

其Bayes误报目标 \(P(\tau<t)\) 使用几何起点先验；非Bayes目标使用 \(1/E_\infty\tau\) 的FAR/ARL口径。本项目 \(P_0(\tau<\infty)\le\alpha\) 是不同约束。不能把两个数值均为0.01当作已公平，也不能因此声称本文全面“更严格/更优”而不比较误报代价和延迟。

当前warm O(J)与其精确候选起点KF库不同：我们把候选状态从监测开始就运行、起点只重启乘积，所以共享倍率使所有起点质量能合并递推。**这是改变候选近似/下注规则后得到的代数降维，不是把其完整精确变化点库等价加速到O(J)。** 文中必须并列说明近似代价；05给同幅值时的收缩失配和半阶矩界，才是这项实现选择的实质支撑。

本文没有在同信息接口复现QUICKDET；不将自行设计的R1称为其忠实复现。可将其作为直接方法竞争和理论比较，必要时另做其条件模型在当前事件选择核下的标准适配。Gupta正文已在本地，不需要用户重复下载。

## 4. 联合信息与KL解释延迟也已有工程先例

Naha, Teixeira, Ahlén and Dey, *Quickest physical watermarking-based detection of measurement replacement attacks in networked control systems*, European Journal of Control71 (2023),100804，DOI **10.1016/j.ejcon.2023.100804**。

本轮读取的本地出版社全文中，§3.3式(23)–(29)定义ADD、SADD、ARL和所需信息率正则条件；式(30)–(34)以非独立观察的条件联合似然构造CUSUM，并将渐近SADD联系到期望条件KL；式(35)/(36)讨论用无条件平稳联合分布的次优CUSUM；§4.1Theorem1式(37)–(40)给攻击后条件创新均值/协方差。Theorem2进一步计算信息量。

其联合对象为innovation与控制watermark，本项目为可信事件、已知量化相位与接收载荷；它是物理闭环、加控制水印和测量替换攻击，本项目是外生状态及发送后加性载荷。这些差别要求重新推导核和健康性能成本，但不能把“联合统计优于边缘统计”“用条件似然而非错误独立假设”“信息量解释检测延迟”写成首次。

此外，联合KL大于边缘KL、事件/条件载荷KL链式分解，本来就是数据处理/链式法则。当前有价值的实验问题是：正确核是否在相同信息、相同误报预算下优于选后创新R0/R1，而非是否优于故意忽略发送选择的错误Gaussian LR。

## 5. 量化、随机编码和水印：不能以量化二字自动独立

已有全文审计给出：

- Shen et al., *Event-triggered nonlinear state estimation with quantized innovations*, JFI362(1),107339，DOI10.1016/j.jfranklin.2024.107339：式(5)指数触发，Theorem1式(6)–(11)及式(28)–(33)量化区间积分，Theorem2通信率。说明事件与量化条件统计已有直接基础；量化对象是前向创新，与本项目反馈中心不同。
- Li–Hu–Guo, *Innovation-Based Tampering Attack on Remote State Estimation With Quantized Observations*, IJRNC36(3):923–934，2026，DOI10.1002/rnc.70168：§2.2、式(25)–(27)及Theorems1–4已有量化前创新篡改、筛选与误差分析；本项目攻击在事件后且前向载荷连续。
- Li–Hu–Guo, *Transmission scheduling for remote state estimation with quantized communication against tampering attacks*, Ad Hoc Networks178,103997，2025，DOI10.1016/j.adhoc.2025.103997：Theorems3–5已有量化篡改参数辨识与估计/调度折中；不应宣称量化下攻击识别是空白。
- Wang et al., *Detection of Perfect Stealthy Attacks on Cyber-Physical Systems Subject to Measurement Quantizations: A Watermark-Based Strategy*, JAS12(1):114–125，2025，DOI10.1109/JAS.2024.124815：既有全文审计核过§II、Theorems1/2和Corollary1；其前向测量量化、闭环及控制/输出攻击与当前不同，但量化水印防御本身已存在。

随机编码方面，旧包保存 Guo, Pang, Sun and Li, *Detection of Stealthy False Data Injection Attacks Against Cyber-Physical Systems: A Stochastic Coding Scheme*，DOI **10.1007/s11424-022-1005-z**。本轮未找到其可核公式全文，因此只把它列为明确待补的编码近邻；不根据题名断言其等价或不等价。

本阶段J即使把 \(r\) 固定为0，也有合法联合核、发送后选择因子位移、Fisher正性和弱幅值 \(b^{-2}\) 充分延迟尺度。因此目前理论**尚未证明这些J能力需要量化或需要随机相位**。量化在这里首先提供了实际中心 \(r\) 的协议场景，不能把整个改善命名为量化专属防御收益。需保留同算法固定相位/公开相位对照，或明确本文仅研究该量化协议下的可实现检测。

## 6. 当前技术链条：哪些是常规具体化，哪些值得继续

|当前构件|技术定位|当前可主张的范围|
|---|---|---|
|联合核 \(\phi_S(u-b-d)h(u-b-r)\)+静默原子|已有选择密度乘法及发送后平移的直接具体化|正确协议建模；不称新概率分布或新似然原理|
|event × conditional payload分解|标准联合/条件概率分解；嵌套归一化给e-factor|公平消融及有效性审查|
|选后MGF倾斜|高斯配方与指数族归一化|合格强基线，不单独包装新算法|
|起点/幅值混合与Ville|标准e-process工具|健康全时域误报保证；已知健康核前提必须保留|
|共享warm倍率的O(J)递推|固定混合权重的代数聚合|真实成本可报告；不冒称精确起点库的等价加速|
|同b初值误差收缩、KL有限regret|稳定线性递推+KL数据处理的具体结合|为warm近似提供可核查边界|
|同b完成平方后的半阶矩界|Gaussian配方、Hellinger与Markov的具体组合|对当前移动选择零点核给明确充分延迟界；全球独创性未证|
|局部 \(1-\mathcal A=\Theta(b^2)\)、\(m_{\rm suff}=O(b^{-2})\)|平方根DQM/Fisher展开的通常局部尺度|关键工作是核实移动二阶零点下的统一正Fisher及warm适用范围；不称新的统计检测阶|

因此，不宜把现有多个标准步骤拆成四五项独立“首次贡献”。可能形成中文方法论文的整体增量，应是：在明确的量化反馈/发送后篡改接口下，给出可在线实现并校正选择的联合审计器，证明warm状态共享的可用范围，并以公平基线证明它在真实检测暴露或后续恢复上值得采用。

这仍是候选，不是创新验收通过。若R1或P已解释全部J收益，应保留较简单方法及负消融结果，不能继续堆混合层数来维持“联合方法”叙事。若固定相位下效果相同，则把随机相位降为可选协议，不强行归因为本轮核心。

## 7. 最小剩余全文需求与当前裁决

当前算法核和延迟证明不因文献缺口而停止。若下一步要主张“随机相位/随机编码方面具有独立机制创新”，优先补一篇即可：

**Guo, Pang, Sun and Li：Detection of Stealthy False Data Injection Attacks Against Cyber-Physical Systems: A Stochastic Coding Scheme，DOI10.1007/s11424-022-1005-z。**

需要核对其编码随机量何时产生、攻击者何时可见、是否在攻击提交后改变观测核、检测器使用的联合记录、有限样本/序贯误报和延迟定理、以及编码带来的健康估计/通信代价。未取得前不宣称本模型与该文定理级排重完成。当前没有请求重复下载Gupta正文、Han或Naha；Gupta补充S1/S2仅在打算继承其最优阈值定理时需要，不是本轮e-process正确性的必需材料。

旧包还留下JFI DOI10.1016/j.jfranklin.2025.108299的元数据线索，但本次未取得可核的完整题名与正文，故不补造题名、不用它作公式级判断，也不扩大用户下载清单。

**裁决：标准工具与直接近邻覆盖度高，具体协议下的算法/保证组合值得实验审查；全球新颖性及量化独有收益均保持OPEN。** 本报告不依赖尚未看到的阶段3实验结果，也不修改冻结实验或正式稿。
