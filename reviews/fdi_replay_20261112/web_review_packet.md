# 网页版GPT审阅材料：FDI / Replay分布式估计的选题筛选

资料日期：2026-11-12

## 审阅任务

请审阅一项“准备投中文学报的增量型分布式滤波安全论文”选题，而不是替作者肯定创新。请重点判断：

1. 文中给出的原始研究问题/权限是否自洽，是否把sensor attack、neighbor estimate packet attack、Replay与Byzantine权限混淆。
2. 所述直接竞争方法与定理是否准确；能否用原论文公式、假设、页码指出遗漏的竞争者。
3. 候选“缓存驻留episode里多次用本地新量测检查同一邻居估计”的具体增量，是否已由Liang 2023、Zhou 2022、Tunga 2018、Qian 2023、AoI/子空间trust工作简单导出。
4. 若不够新，给一个不增加大量检测模块、仍在本研究权限内的最小学报论文问题；或者建议停止。
5. 将文中“文献已证明的事实”“本文从模型推导的事实”“已有实验观察”“待验证假设”分开。不要把摘要命中当全文或把有限仿真说成普遍保证。

以下材料可独立审阅；项目完整28篇全文精读索引、BibTeX和逐页笔记在随附文件中。

## 问题设置

线性离散系统由若干传感器节点观测同一状态：
\[
x_{t+1}=Ax_t+w_t,\qquad y_i(t)=H_ix_t+v_i(t).
\]

节点j在实际发送时广播状态估计\(\hat x_j(t)\)。网络链路\(j\to i\)在该包已经真实发送后才被攻击者替换为另一数值。接收端融合后缓存并在多次本地量测更新中继续使用该值。

拟考虑的弱攻击权限：攻击者知道系统/公开算法和自己的receiver-targeted通信链路，可截获该发送方过去真正发送过的包；不能读接收节点当前本地量测、真实状态、未来噪声/发送，不能读未发送的节点内部估计，不能直接修改触发器或本地传感器。当前没有可信端到端序号、MAC或签名来保证内容新鲜度。一次攻击主要是一条有向边。不把攻击者描述成完整掌控一个节点。

必须分开的攻击：

- additive/step FDI：每个当前合法发送包在链路被加偏置；
- 真实历史Replay：当前包只替换成同一发送方此前实际发出的内容，需报告具体来源时刻和实际内容年龄；
- matched-gap片段Replay：连续旧包按顺序重放且旧包间隔恰好匹配当前接收间隔；
- Yu 2025 reflection attack：根据接收端当前估计构造\(2\hat x_i-\hat x_j\)，需要接收端信息，权限明显更强；
- Xing/Ge历史innovation攻击：使用创新历史及矩阵/协方差设计，不等于字典中的旧estimate replay。

若某候选增加接收端可信时间戳、私有水印、known-safe节点或中心融合器，应作为额外资源明确计入，不能说同一权限。

## 直接竞争方法的具体内容

### Zhou et al. 2022

“Security analysis and defense strategy of distributed filtering under false data injection attacks,” Automatica 138 (2022) 110151，DOI 10.1016/j.automatica.2021.110151。每个节点收到邻居状态估计，算本地measurement residual：
\[
\epsilon^a_{ij}(k)=y_i(k)-H_i\hat x^a_{ij}(k),
\quad D_{ij}(k)=\sum_{\ell=k-r+1}^{k}(\epsilon^a_{ij})^T\Sigma_{ij}^{-1}\epsilon^a_{ij}.
\]
Theorem 1：若rank\(H_i<n\)，接收估计攻击偏差可以落在\(\ker H_i\)，使空间残差看不见，同时估计误差传播增大。防御器对接收估计差\(\|\hat x'_i-\hat x'^a_{ij}\|^2\)用独立指数随机门槛。给定当前差异d，接受概率恰为\(e^{-d/\nu_i}\)。其理论重点包括保护后的稳定/Gaussian条件，不是episode级最坏FPR保证。

### Yang et al. 2019

“Distributed filtering under false data injection attacks,” Automatica 102 (2019) 34–44，DOI 10.1016/j.automatica.2018.12.027。状态estimate与innovation一起传，innovation上的随机保护依指数规则使检测残差保持Gaussian。局部协方差/交叉协方差进入增益与攻击误差递推。Remark明确：只改estimate而保留packet里的innovation可绕过基于innovation的核验。这使攻击字段和包内容权限成为直接模型设计点。

### Liang & Liu 2023

“Event-Triggered Distributed Attack Detection and Fault Diagnosis,” IEEE TIM 72 (2023), 3520111，DOI 10.1109/TIM.2022.3216674。连续时间MAS有耦合agent动态；节点把输出按event-trigger送自身observer与邻居，接收端ZOH保存收到的neighbor output，用UIO估计邻居动态并构造adjacent residual。触发误差进入H∞ residual-generator性能比，UIO存在依rank/ detectability条件。其邻居输出可持续保持，不等于当前项目“多传感器观同一状态、estimate包单次改写、其后接收节点仍持有同一缓存并有新本地量测”的joint covariance；但它是episodic检测最接近的反例来源，必须逐项审查。

### Tunga et al. 2018

“Tuning Windowed Chi-Squared Detectors for Sensor Attacks,” ACC 2018, 1752–1757，DOI 10.23919/ACC.2018.8431073。把每一步Mahalanobis innovation平方相加成滑窗χ²，按Gamma分布定阈值达到目标FAR；与静态χ²和CUSUM比较并推攻击/误差界。它检测同一动态系统中的sensor residual，不是共享邻居cache随机截距，但简单GLS/window/CUSUM必须是episode候选的强基线。

### Qian et al. 2023

“Event-Triggered Distributed State Estimation: A Conditional Expectation Method,” IEEE TAC 68(10), 6361–6368，DOI 10.1109/TAC.2023.3234453。innovation分量按阈值触发，推触发条件下的截断Gaussian矩/条件协方差。无攻击模型，不是缓存包防御；但已经正面处理event selection，禁止把“发送选择改变正常残差统计”写成首次发现。

### Yu et al. 2025

“Distributed Secure State Estimation Against Stealthy Attacks,” IEEE SPL 32, 1930–1934，DOI 10.1109/LSP.2025.3564886。接收端对本地估计与邻居estimate差做χ²。攻击\(m^a_{ij}=2\hat x_i-\hat x_j\)使差反号、平方统计不变；Theorem 1给协方差恶化，Theorem 2给协调多邻居攻击。防御端用历史estimate生成动态编码后发包。攻击者需要实时接收端估计等知识，超出历史包Replay弱权限。

### Huang et al. 2024

“Security Analysis of Distributed Consensus Filtering Under Replay Attacks,” IEEE TCyb 54(6), 3526–3539，DOI 10.1109/TCYB.2022.3209820。攻击真实传感器measurement而非estimate packet，记录周期tau后回放\(y_i(k-\tau)\)，分析协方差和KL残差隐蔽。它说明旧measurement片段以及匹配攻击起始状态有隐蔽风险，但不是当前链路payload字典。

### Xing et al. 2025 / Ge et al. 2026

Xing, IEEE TIFS 20, 4541–4550，DOI 10.1109/TIFS.2025.3564063：截获创新历史，当前攻击是\(T_kz_{k-\tau}+L_kz_k+b_k\)，以滑窗χ²及\(\Sigma_a=\Sigma\)约束，攻击每步优化以扩大MSE。

Ge, IEEE TCyb 2026, 1–13，DOI 10.1109/TCYB.2026.3721072：历史innovation驱动分布式攻击，协方差级隐蔽约束、拓扑block结构与projected gradient。两篇攻击者信息比实际旧包Replay强；证明时间历史可扩大攻击隐蔽集合，防御不能假定“时间分数必抓Replay”。

### 其他必须承认的对照

- Wen & Wang 2018：邻居状态/covariance K-means两簇，majority或known-secure-node cluster，trusted set均值融合；9节点、5恶意对照。
- Güzey & Güzey 2026：中心bearing tracking，NIS/LLR/leaky trust/hysteresis/hold-last Replay/WLS-IRLS，Theorem有dwell/separability/geometry条件，50 MC及ablation。
- Nozal et al. 2022：多跳子空间级trust、不同hop部分信任、re-trust、LMI/CQLF和HIL。
- Zhang–Yang 2026：neighbors交换本地measurement residual、正则映射和滑窗χ²；attacker无实时residual时证明nonzero bias涨检测统计，强攻击时用private watermark。
- Wang et al. 2026：局部不可观、2s-sparse observable、stacked measurement及随算法迭代变化的adaptive saturation；不是neighbor difference单步clip。
- Mitra AoI 2022：time-varying graph state传播有freshness index；Byzantine攻击者可谎报age，算法依图冗余修剪。age不是认证真实性。
- Su et al. 2022 measurement Replay“100% detection”依packet label不可篡改；本题不假定此条件。

DOI速查：Yang 2014 10.1016/j.automatica.2014.05.025；Yang 2019 10.1016/j.automatica.2018.12.027；Zhou 2022 10.1016/j.automatica.2021.110151；Wen–Wang 2018 10.1016/j.dsp.2018.03.002；Liang–Wang 2019 10.1016/j.inffus.2018.04.002；Tunga 2018 10.23919/ACC.2018.8431073；Qiu 2019 10.1109/TIE.2018.2840510；Liang–Liu 2023 10.1109/TIM.2022.3216674；Qian 2023 10.1109/TAC.2023.3234453；Nozal 2022 10.1109/LCSYS.2021.3082309；Mitra AoI 2022 10.1109/TAC.2021.3130882；Huang 2024 10.1109/TCYB.2022.3209820；Yu 2025 10.1109/LSP.2025.3564886；Xing 2025 10.1109/TIFS.2025.3564063；Peng 2025 10.1109/JSEN.2025.3581080；Ge 2026 10.1109/TCYB.2026.3721072；Güzey 2026 10.1016/j.simpat.2026.103318；Wang 2026 10.1109/TASE.2025.3649048；Zhang–Yang 2026 10.1016/j.jfranklin.2026.108914；Su 2022 10.1109/JSYST.2021.3123617。

## 项目前序证据

实际改编基准为五节点、n=2、A=1.01I、Q=.02I、H_i=s_iI、双向环、节点测量每步可得、状态estimate用Send-on-Delta发送及最大静默10；攻击链0→1，t=200–249。它是Yang-form改编，不是原文完整复现，满秩本地量测让local estimator本身很强。

分间隔尾部标定严格同骨架9个主要比较0个过；参考恢复复杂门控6个主要场景0个过。episode缓存均值对CUSUM在强step有局部3–5% receiver MSE gain，但完整12项主比较中5单项过，只有irregular+step场景单元通过，整体1/4失败。half/low偏置、Replay没稳定收益。另一个秩一交替量测压力模型主边0→1的step 4项均未过；反向边更好不能代表主边。

旧Replay字典probe使用64个种子冻结健康sender streams，攻击仅在历史真实发送包里选择，proxy不读receiver当前y；此probe没有闭环estimate轨迹或接收端总体损失结果。risk-greedy原模型预算1仅选59%机会，异质模型选19%，表明低检验proxy与攻击机会/有效注入需分开。它只能作为复现诊断，不能当已证明攻击更强。

详细原始报告和哈希见sources/prior_result_index.json；本包sources/prior_results保留副本。原稿及旧运行目录未修改。

## 本次问题排序

**首推但尚未通过创新门槛：**共享estimate缓存存续期间多次新本地量测形成相关residual的episode-level FDI检验/估计器影响。在同正常episode误隔离率、同packet机会、相同缓存下，能否优于instant residual、Zhou随机保护、Tunga窗口chi-square、corrected-covariance CUSUM，以及Liang的event-triggered UIO？唯一可争取机制差异是同一个旧cache latent error在episode内被重复使用，而非把历史样本假设成独立。直接基线近，必须严查Liang。

**第二优先、作为攻击压力而非论文方法：**单条链路上的选择型historical-state-packet replay。攻击者仅从真实发出的sender估计包字典选值，观察不到receiver当前量测/隐藏状态。相比Yu反射、Huang measurement replay和Xing/Ge innovation attack，其权限更窄。现有探针没有闭环MSE，研究假设仍未验证。

**不作为候选：**另加一个相反号/双残差/饱和模块；更名trust/FPR机制；可信时间戳标签Replay；无水印权限却对比有私钥方案；用单步clip有界宣称全网均方稳定。

## Episode问题的准确数学边界

对节点i在时刻r收到并缓存的邻居状态估计，考虑之后仍未被新包替换时的本地检验残差
\[
r_a=y_i(r+a)-H_iA^a\tilde m_j(r),\quad a=0,\ldots,L-1.
\]
若把packet correction简化成固定加性偏差b，定义共同初始估计误差\(q_r=x(r)-\hat x_j(r)-b\)，则
\[
r_a=H_iA^a q_r+\sum_{s=0}^{a-1}H_iA^{a-1-s}w_{r+s}+v_i(r+a).
\]
若条件于触发/发送历史后的q_r确为Gaussian、均值m_q、协方差P_q，且未来w/v与q_r独立，则
\[
E[r_a]=H_iA^am_q,
\]
\[
\operatorname{Cov}(r_a,r_c)=H_iA^aP_q(A^c)^TH_i^T+
\sum_{s=0}^{\min(a,c)-1}H_iA^{a-1-s}Q(A^{c-1-s})^TH_i^T+
\mathbf1_{a=c}R_i.
\]
这个推导只是带条件的线性系统误差传播。发送包的触发选择、发送方估计与接收端历史会改变q_r的条件分布；确定性Send-on-Delta尤其不能直接假定条件Gaussian。必须先核对事件条件密度或只把同协议下的held-out episode covariance作为经验模型，并报告拟合限制。

“episode-level FPR校准”也只表示在独立tune episodes上使经验误隔离比例接近目标，再在独立audit/test episodes上报告偏差与不确定性。它不自动给有限样本、分布无关、全时域always-valid保证或攻击下估计稳定性；最后一个未被新包结束的episode要单列右删失规则。应同时评估packet opportunities和实际字节。

## 推荐报告阅读位置

| 文献 | 精读定位 | 对当前判断最关键的原文结果 |
|---|---|---|
| Yang 2014 | Automatica 50:2070–2076, pp.2071–74, Eqs.(1)–(11), Thm.1 | 原随机激活Yang型估计器与交叉协方差增益 |
| Yang 2019 | Automatica 102:34–44, pp.36–40, Eqs.(3)–(13), Thms.3,6,7 | estimate+innovation包、随机保护、信息/稳定条件 |
| Zhou 2022 | Automatica 138:110151, pp.110151-2–6, Eqs.(3)–(40), Thms.1–3 | 局部空间残差零空间攻击和随机保护器 |
| Wen & Wang 2018 | DSP 78:92–97, pp.93–96, Eqs.(8)–(18), Alg.1 | K-means状态与协方差聚类、trusted-set融合 |
| Tunga et al. 2018 | ACC pp.1752–1757, Sec.II–IV, Thm.1, Props.1–2 | χ²/CUSUM/window检验和zero-alarm误差 |
| Liang & Liu 2023 | TIM 72:3520111, PDF pp.2–7, Eqs.(12)–(34), Alg.1, Thms.1–3 | 事件触发ZOH邻居输出、UIO attack detection及通信误差 |
| Qian et al. 2023 | TAC 68:6361–6368, pp.6362–64, Assumption 2, Thms.1–2 | 条件Gaussian近似和事件选择后矩 |
| Nozal et al. 2022 | L-CSS 6:506–511, pp.507–10, Eqs.(3)–(13), Thm.1 | 多跳子空间级动态信任与re-trust |
| Huang et al. 2024 | TCyb 54:3526–3539, pp.3528–34, attack (4), Thms.1–7 | measurement片段Replay、KL与稳定/不稳定分析 |
| Yu et al. 2025 | SPL 32:1930–1934, pp.1931–34, Eqs.(2)–(9), Lemma 1, Thms.1–3 | estimate差reflection盲点、多邻居协调与动态编码 |
| Xing et al. 2025 | TIFS 20:4541–4550, pp.4542–47, Eqs.(6)–(39), Thms.1–2 | 历史innovation+当前innovation的KL隐蔽攻击优化 |
| Ge et al. 2026 | TCyb, 1–13, Sec.II–IV, attack (6)–(9), Thms.1–3 | 历史创新与图拓扑约束的攻击设计 |
| Güzey & Güzey 2026 | SMP&T 152:103318, pp.103321–28, Eqs.(14)–(34), Lemma 3.1, Thm.3.2 | NIS/LLR信任、滞回、Replay保持与实验 |
| Zhang & Yang 2026 | JFI 363:108914, PDF pp.2–8, Eqs.(1)–(34), Thms.1–4 | 残差交换、低权限bias与实时残差watermark分层 |
| Wang et al. 2026 | TASE 23:2091–2099, pp.2092–97, Assumptions 1–3, Alg.1, Thms.1–4 | stacked-observation adaptive saturation与2s-sparse observability |
| Mitra et al. 2022 | TAC 67:6349–6365, Author manuscript Sec.VI, Alg.2 | 可伪造AoI和多跳图冗余修剪 |
| Su et al. 2022 | Systems Journal 16:5720–5728, pp.5722–27, Remark 2, Thm.1 | 不可篡改packet label条件下的measurement Replay |

以上是重点选择的16篇方法级近邻，不等于全部28篇的列表；其余本地PDF、每篇DOI/哈希和页码定位在研究组自己的阅读表。文献里“安全/有界”的定义各异，不可合并成同一保证指标。

## 给网页版GPT的具体审阅请求

1. 请逐条检验episode主问题是否已由Liang–Liu 2023 UIO、Qian条件滤波或Tunga窗口χ²直接覆盖。特别比较状态空间、交换变量、缓存保持、持有本地量测、攻击何时/能否改包、检测统计和FPR定义。
2. 请对候选状态方程写出r_0:L在发送/触发条件下的联合均值和协方差，指出还需哪些cross-covariance，以及event-selection如何改变分布。不要默认r_a iid。
3. 请判断字典式Replay是否与Yu反射型或Huang周期Replay构成不同攻击类，并指出“只能重放同一sender真实旧estimate”的限制是否有实际意义和可实现性。
4. 请给出一项最小判败实验及公平基线；不要建议大而全的集成网络。请明确若什么结果出现应停止立题。
5. 请把已证明事实、模型推断、项目实测和待验证假设分层，不把当前本地检查写成论文新定理。

## 下载声明

本轮新下载成功PDF为0。Yu SPL 2025和Xing TIFS 2025是用户刚放入Zotero的全文；我只读复制并核对哈希。其余核心PDF复用现有本地/Zotero库。代理没有发邮件或联系作者。附属来源索引含28篇全文DOI、卷页、页面数和SHA-256；原件及文本在本地忽略目录。
