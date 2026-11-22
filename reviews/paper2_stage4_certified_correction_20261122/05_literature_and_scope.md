# 阶段四：污染认证与输出校正的文献和权限边界

日期2026-11-22。基准提交e1c55269。本轮只核读本地已有资料及用户新附件，没有网络检索、没有下载新全文、没有生成随机性能样本，也未修改阶段三或正式稿。

**判断：可以继续证明“历史起点信息有限，而当前污染功能仍可认证”的模型特定关系；不能把似然置信序列、参数估计后补偿或二次风险最优化单独列为新原理。** 新增2026年识别补偿论文是直接近邻，但本地未找到全文，当前不能认定完整创新性通过。

## 1. 证据分层与实际核读范围

| 文献/资产 | 本轮得到的证据 | 可以作出的判断 |
|---|---|---|
| Likelihood Ratio Confidence Sets for Sequential Decision Making，用户标为NeurIPS2023 | 用户给定题名与年份；在仓库、原研究文献目录及Zotero文本缓存的定向检索中未命中全文 | 作为必须补核的直接统计工具近邻；不编造作者、公式号或DOI |
| Howard等，Time-uniform, nonparametric, nonasymptotic confidence sequences | 本地作者稿TXT，arXiv:1810.08240v9，文件页首为2022-08更新；本轮核读§1定义及混合鞅综述段落 | 全时域置信覆盖、下置信序列和混合鞅不是新的统计概念 |
| Remote estimation with binary-switching sensors under tampering attack: Identification-compensated method using quantized communication，用户标为2026 | 用户提供题名、ScienceDirect PII S1570870526001356；定向本地检索未找到全文或独立题录缓存 | 可列为最优先获取的工程近邻，不能依据题名断言其定理已覆盖或未覆盖本项目 |
| Khazraei–Pajic，Attack-resilient state estimation with intermittent data authentication | 本地作者稿全文、NSF来源记录及Crossref缓存；本轮核读摘要、§4、Definition3、Theorems4–5 | 间歇认证与估计误差保证已有直接工作，但其信任来源与本轮统计置信下界不同 |
| Li–Hu–Guo，Ad Hoc Networks2025及IJRNC2026量化攻击工作 | 复用已有公式级全文审计，不冒称本轮重读全部PDF | 量化、攻击参数辨识与估计/调度折中已有近邻 |
| Gupta等，Signal Processing2026 QUICKDET | 复用阶段三本地正文审查 | 未知起点与攻击模型的条件似然、候选滤波和序贯检测已有直接近邻 |
| 本仓库G1-R风险约束恢复研究 | 本轮读取旧数学审计与实现合同 | 当前影响集合、不能唯一归责时的补偿及风险预算在项目内部已有研究，须明确阶段四的新旧差别 |

本轮检索覆盖当前仓库reviews、原mypaper研究目录中相关TXT/JSON/Markdown及Zotero的可读缓存，不等于全盘扫描或全球文献检索。没有命中只说明本轮未找到，不能说论文不存在。

本轮直接核读文件的来源标识：

- Howard文本：原研究目录 references/trajectory_certificate_20261013/Howard2021_ConfidenceSequences.txt；SHA256 b4b9bc1bee40d8e00c0017dfb09ae99f8ae385e4f00d2de17e79f5adbea8ab77。文件名含2021，但本文使用其页首显示的2022更新作者稿，不把文件名当作版本年份。
- Khazraei作者稿文本：references/trigger_conditional_20261009/architecture_neighbors/Khazraei2022_IntermittentAuthentication_NSF.txt；SHA256 e9d5f49118243b943db3428951b3531016191ce7d0767d1522275f0edcb6e69f。本地来源记录为 [NSF PURL 10319604](https://par.nsf.gov/servlets/purl/10319604)，作者稿页首为2020-05-16。
- 正式题录缓存：原mypaper/literature_review/survey_search/cache_targeted_2026-11-10/recovery_crossref_3.json。其条目匹配PII S000510982100563X，正式卷为Automatica138，文章110035，2022-04，DOI [10.1016/j.automatica.2021.110035](https://doi.org/10.1016/j.automatica.2021.110035)。本轮正文定位使用上述作者稿，不能伪称已重读2022正式版全文。

第三方全文留在原位置，本包不复制上传。

## 2. 似然反演置信集合：标准工具与必须满足的条件

Howard作者稿§1式(1)已经把置信序列定义为

\[
\Pr(\forall t\ge1:\theta_t\in C_t)\ge1-\epsilon,
\]

并明确下置信序列、连续查看数据及混合鞅的历史来源。用户另给的NeurIPS2023题目直接指向似然比置信集合，因此更不能把

\[
C_t=\{\vartheta:p_{\vartheta,t}>\epsilon q_t\}
\]

以及通过Ville不等式得全时域覆盖称为原创统计方法。本文未取得该NeurIPS全文，故不声称其具体预测分布条件与本项目完全一致；这条标准似然鞅证明应在项目内自洽建立，同时补核直接引用。

本阶段可以研究的是该工具怎样在本通信协议中合法落地：

1. 分母必须是参数 \((k,b)\) 对**实际接收记录**的精确概率密度，不能用warm近似状态冒充每个真实起点的候选后验。
2. 分子 \(q_t\) 可以来自预先规定、每步正规化且序贯一致的预测分布。参考Q不必是真实攻击模型，但不能把任意事后选择的检测分数都当作同一个一致Q。
3. P1/J1作为分子与它们作为分母是不同用途。分子失配影响效率；分母失配会破坏覆盖，二者不能混淆。
4. 真幅值不在分子候选网格并不破坏精确分母反演的逐参数覆盖；有限字典收缩证明却不能因此自动覆盖连续幅值。
5. 若近似优化给出参数集合的外包络，投影所得污染下界更保守，可以保留安全性；未经证明删除旧起点或幅值区间会抬高下界并破坏覆盖。

这些是模型适配、可计算认证及误差语义的问题，不能单凭使用置信序列就宣布“认证算法”完成。

## 3. 间歇数据认证并不等于本轮统计污染证书

Khazraei–Pajic作者稿研究有界噪声LTI系统中的稀疏/批处理弹性状态估计与两种检测器，主要对象是perfect attackability，即隐蔽攻击能否造成无界估计误差。

§4 Definition3规定认证时刻 \(t_k^i\) 上对应通道的攻击严格为零：

\[
a_i(t_k^i)=0,
\]

且认证间隔有界。Theorem4以含认证传感器行的观测矩阵满秩刻画特定窗口的不可完美攻击性；Theorem5在指定系统类别、可观测认证传感器集合与有界认证间隔下排除完美攻击。其信任来自密码学完整性约束或等效的真包保证。

本轮没有新增已认证载荷。所谓“污染认证”是正确概率模型下、失效概率为 \(\epsilon\) 的全时域统计置信证书：

\[
\Pr(\forall t,\ 0\le L_t\le\theta_t^\star)\ge1-\epsilon.
\]

它不认证某个历史载荷为真、不产生不可伪造的新鲜检查点，也不保证每条样本路径实际平方误差逐拍下降。即使单次条件风险改善成立，统计覆盖失败仍会产生代价，故需单独保留期望风险预算。

因此不建议将英文工作名称中的“certified”不加解释地等同于“authenticated”。更准确的描述是“statistically certified contamination lower bounds”或直接“time-uniform confidence bounds for contamination”。近邻的有界噪声/任意受攻通道保证与本轮Gaussian/固定同向幅值保证也不能互比为谁全面更强。

本地已具备这篇作者稿及正式题录，无需用户重复下载它来启动当前推导。

## 4. 量化识别补偿：新增2026论文必须逐式核读

用户给出的 [ScienceDirect条目](https://www.sciencedirect.com/science/article/abs/pii/S1570870526001356) 题为：

*Remote estimation with binary-switching sensors under tampering attack: Identification-compensated method using quantized communication*。

本轮只拥有用户提供的题名、年份和PII，没有独立核读其摘要或正文。故不补造作者、期刊卷页、DOI、算法公式或性能结论。题名足以使它成为“攻击识别后补偿＋量化通信”的高优先近邻，但不足以判断其是否已包含全时域置信覆盖、错误起点不辨识或风险下界校正。

取得全文后应按以下映射核查，而非只比较标题：

| 要核查的原文部分 | 本项目对应量 | 需要决定的问题 |
|---|---|---|
| 二值开关传感器、量化对象与通信反馈 | 本项目量化预测反馈，前向发送载荷连续 | 是同一个观测核，还是不同量化位置/条件分布？ |
| 攻击发生位置和可用信息 | 真实事件先生成，只有发送后修改载荷 | 原文是否允许改事件、量化前输入或识别探针？ |
| 攻击参数的识别目标与保证 | \((k,b)\) 的精确似然及污染函数 \(bH_{k,t}^+\) | 是渐近点估计、后验一致性、固定时刻区间，还是全时域置信序列？ |
| 补偿/恢复更新 | 输出 \(m_t^a-L_t\)，monitor反馈保持原样 | 是否已经提出相同的保守下界校正及同轨道风险比较？ |
| 误辨识和未知起点 | 全时域覆盖失败预算、起点有限信息与当前影响遗忘 | 是否已给功能收缩而无需起点一致辨识？ |
| 有限通信与模型失配 | 本轮理想精确中心/连续载荷 | 原文若已有有限比特真实实现，不能忽略其更强工程范围 |

相关的本地已得全文审计可先限制宽泛创新叙事：

- Li、Hu、Guo，*Transmission scheduling for remote state estimation with quantized communication against tampering attacks*，Ad Hoc Networks178，103997（2025），DOI [10.1016/j.adhoc.2025.103997](https://doi.org/10.1016/j.adhoc.2025.103997)。已有审查定位Theorems3–4的篡改概率辨识及Theorem5辨识误差/估计误差折中，见[既有比较](../paper1_quantized_literature_fulltext_audit/02_jfi_adhoc_comparison.md)。
- Li、Hu、Guo，*Innovation-Based Tampering Attack on Remote State Estimation With Quantized Observations*，IJRNC36(3):923–934（2026），DOI [10.1002/rnc.70168](https://doi.org/10.1002/rnc.70168)。已有审查定位其量化前创新攻击、候选Gaussian假设和估计性能定理，见[公式审查](../paper1_quantized_literature_fulltext_audit/04_li_hu_guo_wiley_equation_audit.md)。

这两篇与新增PII论文不能被当作同一论文或相互替代。当前不声称“量化下攻击参数识别和补偿”尚无人研究。

## 5. 项目内部已有功能集合和风险校正，不应重复命名

仓库此前G1-R研究已经讨论：事件归责不唯一时，把候选参数集合映射成当前污染影响集合，再选择零/部分输出补偿；且区分恢复健康反事实和真实MSE改善。依据为 [02数学审计](../g1r_risk_constrained_recovery/02_mathematical_audit.md) §2、§5–7和[03实现合同](../g1r_risk_constrained_recovery/03_problem_and_implementation_contract.md) §3–5。

该旧问题是五节点二维、固定外生发送日程、一次Replay攻击、有限历史事件字典；其污染对象是受攻估计相对健康反事实之差，真实误差差中保留健康误差交叉项。标准集合反演/置信椭球、凸包分离风险动作和误补偿预算已明确作为标准工具。故不能把“多个攻击解释映射到当前影响、无需唯一归责”这一口号当作全新研究发现。

本轮可能的实质差别是：

- 固定同向持续载荷攻击，在可信随机事件反馈机制下使用精确条件似然；
- 污染 \(\theta_t=m_t^a-\mathbb E_\vartheta[x_t\mid\mathcal I_t]\) 针对**真实参数下同一接收历史的条件均值**，不是另一条健康反事实估计；
- 固定同幅值不同起点的未来总辨别信息有限，而对当前污染的差异会遗忘；
- 将这种区别用于精确全时域置信集合的功能收缩，再以污染下界而非区间中心作风险改善最优校正。

当前条件风险的交叉项消失，来自条件均值的正交性，而非证明一般错误估计器融合可以忽略相关性。新结果的写法必须保留这种不同评价对象。否则容易把旧反例已经否定的“恢复健康反事实必降低MSE”重新引入。

## 6. 中心/码字权限与阶段四定理的范围

阶段三算法实际读取精确中心残差 \(r_t=c_t-m_t^-\)，原始相位字段未单独输入。精确中心与已知预测允许恢复实际触发中心，因此当前固定参数下的发送/静默后验仍高斯，污染系数可由事件增益递推。

真正仅保留整数索引的序贯记录不同：静默更新依赖未记录的中心，下一预测一般不能仅由索引历史重建，隐藏中心混合还可造成非Gaussian后验。阶段三的index核只能在给定已知先验下作单步投影；不能直接将其连乘当作阶段四精确候选似然，也不能自动继承 \(P_t^\vartheta=P_t\) 与 \(\theta_t=bH_{k,t}^+\)。

因此本轮污染置信序列和同轨道条件MSE校正应先限定于**接收端可用精确中心及连续接收载荷**。用户所说“只记录量化中心或码字”若在设备上指精确重构中心，落在该范围；若指仅整数索引，则需额外的隐变量滤波/记录闭合证明。这个约束是理论适用域，不要求中断当前已授权的中心可见分支推导。

## 7. 当前候选增量、不能主张的内容与验收

| 阶段四构件 | 技术定位 |
|---|---|
| \(q_t/p_{\vartheta,t}\)鞅、Ville反演置信序列 | 标准统计工具；需补核用户给的直接NeurIPS近邻 |
| 参数集合投影到 \(bH_{k,t}^+\) | 标准置信集合映射；任务特定对象与计算机制需明确 |
| \(\arg\max_{c\ge0}\inf_{\theta\in[L,U]}(2\theta c-c^2)=L\) | 基本一维二次极小极大优化，不单列新原理 |
| 覆盖失败的 \(2\epsilon TB_{\max}^2\) 期望风险惩罚 | 标准分事件风险界；贡献需体现精确模型常数和可用认证效率 |
| 同幅值不同起点的有限总KL与当前影响指数遗忘 | 值得作为模型结构命题核查，不能扩大为所有攻击起点都不可识别 |
| 有限幅值字典、可数起点的当前污染功能收缩 | 需要解决晚起点计数、未来起点同健康尾和参数真值范围，是较实质的证明义务 |
| 连续幅值的一维全局似然上包络和保守计算 | 若保持集合包含与全时域覆盖且可实际产生足够大的L，是潜在算法增量；粗网格不构成认证 |

整体候选贡献应写为：在规定可信记录和持续发送后加性攻击模型中，建立“起点历史未必可精确辨识—当前污染功能可认证—输出校正有条件风险预算”的理论联系，并给可验证的计算接口。

这仍不等于恢复工程成功。还须证明或验证：置信下界达到预定有效增益 \(L_t^2\ge g\) 的速度、实际校正的期望累计MSE收益，以及计算上包络误差不会把下界抬高。长静默可使真实污染也变小，故不能不加条件保证固定g最终达到；有限字典收缩更不能直接当作连续幅值算法的效率证明。

## 8. 最小补充阅读需求

当前理论推导不必等待外部全文，可以继续在模型内完成。但在把结果写成论文贡献前，优先取得两份材料：

1. **最高优先：** *Remote estimation with binary-switching sensors under tampering attack: Identification-compensated method using quantized communication*，用户提供2026，PII **S1570870526001356**，[出版页面](https://www.sciencedirect.com/science/article/abs/pii/S1570870526001356)。需要完整正文及补偿/识别相关定理，重点核对第4节对照表。当前不能给出未核实DOI。
2. **统计工具直接近邻：** *Likelihood Ratio Confidence Sets for Sequential Decision Making*，用户提供NeurIPS2023；需正文和附录。[NeurIPS官方论文库](https://proceedings.neurips.cc/)可按完整题名定位。需要核对参考预测分布条件、似然反演的覆盖量词及收缩/计算结论。本轮不补造精确论文URL、作者或公式编号。

无需为本轮重复下载Khazraei作者稿、Howard作者稿或Gupta正文；本地已有可用材料。若两份新文献最终未取得，结论应保持“数学模型内推导可继续、全球新颖性和补偿方法排重尚未闭合”，不能把缺文献变成肯定的创新结论。
