# 三篇自适应检测近邻：公式级审查

状态标签：**FULLTEXT** 表示取得并阅读正文；**OPEN** 表示仅题录/摘要或全文仍缺。第三方PDF留在本地Zotero或临时目录，不提交仓库。来源与哈希见 `sources/source_manifest.json`。

## 1. Zhang, Chai & Wang：RACKF

**FULLTEXT** “Resilient adaptive covariance Kalman filter for state estimation under false data injection attacks,” *Asian Journal of Control*, 28(3), 1600–1610 (issue year 2026; received 2024-06-20, accepted 2025-04-29), DOI [10.1002/asjc.3722](https://doi.org/10.1002/asjc.3722)。原文第1600–1610页均核读；Zotero PDF SHA256 `eca461f52d40f4bfaea9def0577d2dcbc8981f2bf03530304234c4d76a6cc67b`。

**模型与具体公式**：式（4）–（6），p.1602，将传感器测量攻击建模为 `y_k=Hx_k+v_k+eta_k a_k`，攻击发生变量 `eta_k` 为Bernoulli但其概率/向量未知。式（7）–（9），p.1603，依据预测残差自适应饱和边界 `sigma_k`，残差大时收缩边界。式（10）–（11），p.1604，对饱和创新 `ey,k` 设置阈值触发 `mu_k`，并使用

```text
R_a,k = R_k + mu_k (ey,k^T ey,k) I,
mu_k = 1{ ey,k ≥ kappa sqrt(sigma_k) }. [按原式(11)抄录，未添加范数]
```

滤波校正式（14）–（16），p.1604，以 `R_a,k` 替换原量测协方差并以饱和残差更新状态。其核心已是“FDI期间由预测残差触发的自适应协方差加鲁棒饱和”，不能宣称本候选首次将自适应协方差用于FDI。

**理论结果**：Assumptions 1–3，pp.1604–1605，要求过程协方差时不变、`(A,Q^(1/2))`可稳定、`(A,H)`可检测、A可逆，并要求攻击注入有界 `||a_k||≤mu`。Theorem 1，p.1605，另需给定参数和矩阵使式（23）–（26）的块LMI `G_k≽0`；得到预测误差有界式（27）及渐近界（28）。这是估计器鲁棒性/误差界，不是“误报率由可信本地通道控制”的定理。

**与本候选的差异和竞争**：RACKF修改Kalman校正过程，利用攻击影响过的测量残差剪裁并触发 `R_a,k`；候选保持Yang估计器不变，拟用另一条本地通道估计正常尺度后检测。目标和信息源不同，但风险分界高度直接：候选不能把“自适应协方差+残差触发+未知FDI”本身列为贡献；必须证明并验证可信来源带来RACKF缺少的虚警/检测能力。本轮没有同模型复现RACKF，不能声称胜过其定理或实验。

**FACT / DERIVED：定理边界及原图歧义。** p.1605式（21）明确使用“without process noise and measurement noise”的动力学；Theorem 1依此证明，不能迁移为持续Gaussian噪声下的逐路径误差界。p.1606式（35）–（36）的核心是 `V_(k+1)≤(1−alpha)V_k+lambda_max(U)mu²+xi`，并非正常统计尺度的覆盖率。p.1603式（8）印刷指数为正 `gamma1 epsilon exp(epsilon)`，相邻解释及Theorem 1却使用负指数。式（11）直接用向量残差与标量阈值比较，未给出范数/分量规则；式（7）定义sat_sigma的界为sqrt(sigma)，式（15）又写sat_(sqrt(sigma))。已核原图，保持印刷与解释差异，不静默替作者选实现，也不把疑点当作本项目贡献。

## 2. Liu et al.：DCI自适应协方差、NIS与反制闭环

**FULLTEXT** “Detection and countermeasure integrated framework against false data injection attacks in multi-area coupled power systems,” *Nature Communications*, 17:7379 (2026), DOI [10.1038/s41467-026-74374-5](https://doi.org/10.1038/s41467-026-74374-5)，19页；取得全文PDF SHA256 `0b499060f7a86177c8cc3bc17f8ddec7652e711fd1175f38b901d305a8bd5335`。

**自适应公式**：Box 1，印刷页16，在集中式UKF/AUKF中由估计残差更新

```text
Q_k = eta Q_(k−1) + (1−eta) K_k d_k d_k^T K_k^T,
R_k = eta R_(k−1) + (1−eta)(epsilon_k epsilon_k^T + C_k P_k^pri C_k^T),
d_k = y_k − C_k xhat_k^pri,
epsilon_k = y_k − C_k xhat_k^post.
```

因此，协方差校准和检测都使用同一系统测量/估计通道；FDI污染的 `y_k` 也进入 `d_k`、`epsilon_k` 和在线 `Q_k,R_k` 更新。式（23）–（26），印刷页17，定义 `epsilon_k=C_ke_k`、`r_k=epsilon_k^T epsilon_k`、`lambda_k=epsilon_k^T S_k^−1 epsilon_k`，并宣称无攻击时NIS服从 `chi²_m`，以 `tau=chi²_alpha(m)` 判决。该文明确提出动态噪声环境下自适应协方差与统计阈值，且进一步接入反制控制。

**范围差异**：该文是集中式多区域LFC的非线性UKF，传感器测量FDI，目的为估计/检测/反制；它没有隔离出仅使用接收端本地量测的独立可信尺度通道，也没有Yang估计链路残差。故自适应协方差/NIS不是新颖点；“同一受攻数据用于在线协方差，可能造成尺度污染”则为候选剩余问题，但需公平对照RACKF/其类方法。

**DERIVED：不可照搬的卡方结论。** p.17式（23）用后验残差，式（25）却使用“innovation covariance”。在线性Gaussian KF中，后验残差 `epsilon=(I−HK)nu` 的协方差应为 `(I−HK)S(I−HK)ᵀ`，一般不等于先验创新S。数据自适应S也不自动给精确卡方分布。因此上文记录的是作者主张，不是本审查独立认可的有限样本FAR定理。p.17–18式（29）–（41）另外分析名义观察器Schur稳定和增广LMI可行时的扰动/ISS保证，不涉及可信尺度的统计覆盖。

## 3. Bhattacharya et al.：自适应CUSUM参数化

**FULLTEXT** “Adaptive Parameterisation for Efficient Detection of False Data Injections,” *ACM Transactions on Embedded Computing Systems*, 25(1), Article 17, 30 pages (January 2026), DOI [10.1145/3777903](https://doi.org/10.1145/3777903)。Zotero全文SHA256 `4daa122961ee47d9f453a71175e53ecd7bfaad61ea5efc968fbd99e39854928d`。

**检测模型**：式（1）–（5），期刊编号17:5–7，定义LTI/Kalman残差 `r_k=C e_k+eta_k`、`g_k=r_k^T Sigma^−1 r_k`；正常时假设 `r_k~N(0,Sigma)`、`g_k~chi²_m`；CUSUM `S_k=max(0,S_(k−1)+g_k−b)` 并以阈值 `tau` 报警。

**自适应参数**：Definition 1及Claim 1，17:7–9，研究已知系统与检测参数的成功隐蔽FDI；第6节Theorem 1、Algorithm 1–2，17:12–16，用离线状态空间划分计算攻击使状态越安全界的最小时间 `k_min`。式（23）–（28），17:18–19，依据攻击使 `g_k`统计变化而切换到仅预测状态；Algorithm 3及式（29）–（30），17:20–21，在观察窗口均值偏离名义 `E[g]=m`时，按状态区间和剩余检测时限调CUSUM bias `b_k`，使报警早于最小攻击时间。其方法自适应的是状态安全裕度驱动的CUSUM bias，而不是正常噪声协方差估计；但“动态调整检测器参数、在噪声下考虑FAR”已明确被覆盖，不能作宽泛首创主张。

**与候选的边界**：该文不提供本地可信参考通道，也没有估计全局噪声尺度；问题聚焦于已知LTI状态空间下对危险隐蔽攻击的提前发现。它不直接覆盖可信本地协方差校准，但直接限制“在线自适应检测参数”作为算法贡献的宽度。

**FACT / DERIVED：精确对应与限制。** 式（30），17:21，为 `b_k = b/3 + (S_hat−tau)/k_det − d_b`，其中d_b>0；该文利用所选攻击族的 `E[g]=b/3` 选择累计漂移。它改变CUSUM偏置，既不等于本候选的chat，也不估计变化后的正常协方差。正文将未来样本均值用期望替代的步骤不能单凭自身推出逐路径必在k_det内报警；本轮不把这种表述直接当作有限样本保证。要严格互推，还缺可信通道信息、噪声共同尺度假设和chat覆盖事件，不能靠换符号补齐。

**公式审慎说明**：该文Theorem 2，17:18，文字声称攻击下 `g_k=sum_i q_(k,i)^2` 服从均匀分布；其后Eq.(24)–(26)实际推的是独立均匀分量平方和的均值/方差，不是 `g_k` 的均匀分布。故不把其Theorem 2的分布形状作为可信竞争定理；其CUSUM参数化机制及算法流程仍然是正文明确存在的竞争工作。

## 4. 直接竞争结论

|候选表述|审查判断|
|---|---|
|“首次使用自适应协方差/卡方或NIS检测处理噪声变化”|不成立；DCI式更新和NIS门限已直接覆盖自适应估计/检测框架，RACKF进一步直接用于未知FDI及残差触发协方差|
|“首次动态调整检测参数兼顾攻击发现和误报”|不成立；ACM 2026已调CUSUM bias、监测残差统计并把噪声/FAR作为目标|
|“可信本地参考隔离校准与链路攻击污染”|在三篇所核全文中未见完全相同结构，但仅是结构区别；是否有新性能/保证需检验，不能由未见同名公式推出创新|
|“Yang分布式链路攻击的实际增量”|三篇与本轮全同步Yang链路模型不等价；oracle只是理想参考，未超过oracle不是否决标准。需要相对同权限可部署强基准的证据，本轮同校准预算pilot尚未建立增量|

第三篇Wiley论文现已取得并核读；未获取全文的文献为本任务之外的项目既有排重资产，不在此用来作“无竞争”推断。
