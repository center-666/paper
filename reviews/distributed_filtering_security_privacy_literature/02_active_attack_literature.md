# 02 主动攻击检测与防御：公式级精读

## 1. Yang 2014：基准估计器而非安全算法

2026-11-14复读修订：本页对“原文定理”的叙述不代表已独立证明。13号报告核实Yang2014印刷式(13)和Lemma 7存在问题，并反驳Zhou2022式(34)最后一个似然等式；有关随机通信协方差和Gaussian闭合不能直接作为本项目保证。原算法与既有实验证据分别保留。

Yang et al., Automatica 50 (2014) 2070–2076, DOI 10.1016/j.automatica.2014.05.025，PDF pp.2071–2072 式(1)–(5)。系统为

\[
x(k+1)=Ax(k)+w(k),\qquad y_i(k)=\gamma_i(k)(H_i x(k)+v_i(k)),
\]

其中过程噪声、量测噪声、初始状态和独立 Bernoulli 激活变量相互独立，激活概率为 q。估计器为

\[
\hat x_i(k+1|k)=A\hat x_i(k|k-1)+K_i^p(k)(y_i(k)-\gamma_i(k)H_i\hat x_i(k|k-1))
-\epsilon A\sum_{j\in N_i}\gamma_j(k)(\hat x_i-\hat x_j).
\]

式(5)的误差递推包含节点交叉误差项，正文式(6)–(9)显式引入 \(E[e_i e_j^T]\)。原文定理和引理针对无攻击随机激活下的协方差上下界、增益条件和均方稳定性（期刊pp.2073–2076），但复读发现印刷(13)缺少随机切换方差项、Lemma 7的全空间严格LMI不可行，不能不经核查继承；详见13号报告和独立有理数核查。

**可迁移内容：** Yang-form 的本地量测项、邻居一致性项和交叉协方差递推。

**不能直接迁移：** 项目协议是估计值 Send-on-Delta/固定外生日程+缓存外推；不是每次用 Bernoulli \(\gamma_i(k)\) 直接决定邻居当前值。攻击会使发送和接收误差相关，不能把原定理当作安全或缓存定理。

证据：FULLTEXT；模型迁移判断为 DERIVED。

## 2. Yang 2019：随机保护器已经处理链路 FDI 的直接先例

Yang et al., Automatica 102 (2019) 34–44, DOI 10.1016/j.automatica.2018.12.027。PDF pp.35–36 式(1)–(7)给 Yang-form 估计器；攻击模型在 p.35–36 式(4)为链路上以概率 \(\xi_q\) 注入零均值 Gaussian bias \(\rho\alpha_{ij}(k)\)，协方差 \(\Theta_{ij}\)。攻击事件与攻击值独立，并假设包中的 estimate 和 innovation 不标记。

接收保护器在 p.36 式(5)–(6)按邻居 innovation 的二次量产生随机丢弃概率：

\[
\gamma_{ij}(k)=\mathbf 1\{\alpha>\phi(\Delta_j^\star(k))\},\quad
\phi(d)=1-\exp[-\tfrac12 d^TZ_j^{-1}d],\quad Z_j=3\|R_j\|.
\]

这里的 \(\alpha\sim U(0,1)\) 在接收端生成；目标是保持估计器和 innovation 的 Gaussian 性，而非确定性硬门控。正文 p.37 Remark 2 说明攻击者难以区分 estimate 与 innovation 字段；如果攻击者只改 estimate、保留可验证 innovation，这个保护器的假设会改变。

pp.38–41 的协方差递推、Theorem 3、Theorem 6 和后续稳定性结果保证的是指定 Gaussian 随机注入和强连通/可控等条件下的误差性质，不是对任意通信载荷篡改或任意 Replay 的 universal guarantee。

**排重结论：** 随机残差保护、攻击下的 distributed filtering 和 Gaussian 性质已有先例。把随机门控改成“可信权重”不能自动成为新方法。

## 3. Wen & Wang 2018、Liang & Wang 2019：空间信任融合已被直接研究

Wen & Wang, DSP 78 (2018) 92–97, DOI 10.1016/j.dsp.2018.03.002。PDF p.92 abstract 与 pp.93–95 式(1)–(8)：节点发送 \(\hat x\) 和协方差；对邻居估计用 K-means 分成两个簇，取 trusted cluster 做均匀融合；对协方差另做组合。攻击场景包括 random、FDI、Replay。仿真为 9 节点无线网络，含 secured/normal/compromised 节点。它额外发送协方差，且其 secured-node/聚类结构不能直接当作一跳 Yang 同权限方法。

Liang & Wang, Information Fusion 46 (2019) 44–50，作者稿 PDF pp.9–13 式(8)–(18)和 Algorithm 1：状态与协方差分别聚类，最大簇作为 trusted set，再 diffusion Kalman。其主要条件是少于半数节点受攻、邻居状态可互比；同时展示 random/FDI/Replay。

**结论：** “空间一致性+可信加权+Replay/FDI”已有直接技术竞争；新工作必须改变信息权限、性能对象或可证明保证，不能只换权重公式。

## 4. Zhou 2022：邻居估计空间盲区

Zhou et al., Automatica 138 (2022) 110151, DOI 10.1016/j.automatica.2021.110151。PDF pp.2–4 式(1)–(15)及 Theorem 1：邻居估计被 \(z_{ij}(k)\) 篡改，接收节点用本地量测形成残差。若本地 \(H_i\) 秩亏，则可取非零 \(\Xi\) 满足 \(H_i\Xi=0\)；攻击构造让邻居差被抵消而残差正常，同时共识项被 \(\lambda A\Xi\) 驱动。该结论是检验统计量的空间零空间漏洞，不等于任意攻击均隐蔽。

其随机保护在pp.4–7式(20)–(24)用指数随机变量和估计差产生接受概率，原文Theorem 2–3声称谱条件下的安全/估计性质及Gaussian形态。复读发现式(34)将拒收概率错误改写成常数乘Gaussian二次指数，相关证明步骤不能继承，见13号报告。该随机保护使用本地估计和收到的邻居信息，仍是可执行的直接强基线；证明问题不等于本项目已经超过其性能。

**可借鉴：** 任何新方法必须报告 \(\operatorname{ker}H_i\) 条件；对部分观测不能把空间残差报警当作可检测性证明。

## 5. Replay 与历史数据

### 5.1 Su 2022

Su, Ye & Zhao, IEEE Systems Journal 16 (2022) 5720–5728, DOI 10.1109/JSYST.2021.3123617。PDF pp.5721–5722 式(1)–(6)：多传感器观测和分布式 observer。攻击者知道实时所有测量，可把 \(y_{i,k}\) 改为历史 \(y_{i,k-r(T_2-T_1+1)}\)，并以包计数/标签 \(m_i,n_i\) 检出 Replay（p.5722 Remark 1–2）。Theorem 1–3（pp.5722–5724）以 LMI 给误差系统稳定和 \(H_\infty\) 性能；隔离受攻 sensor 后只用 secure sensors。

**关键限制：** 原文假定攻击者无法修改 packet label，因此所谓 100% 检测不是无认证一跳历史状态包的保证；原文攻击的是传感器量测，非当前 Yang 邻居 estimate payload。

### 5.2 Huang 2024

Huang et al., IEEE TCyb 54 (2024) 3526–3539, DOI 10.1109/TCYB.2022.3209820。PDF pp.3527–3531 的攻击式和 Theorem 1–7分析固定长度历史量测 Replay 的误差协方差、稳定/不稳定系统和 KLD/残差隐蔽性。它研究的是量测通道，不是邻居 estimate 缓存；因此是 Replay 统计基准，不是当前攻击入口的直接算法。

### 5.3 Xing 2025、Ge 2026

Xing et al., IEEE TIFS 20 (2025) 4541–4550, DOI 10.1109/TIFS.2025.3564063，PDF pp.4542–4545 式(1)–(9)：攻击者截取历史 innovation，使用

\[
z^a_{i,k}=T_{i,k}z_{i,k-\tau}+L_{i,k}z_{i,k}+b_{i,k},
\]

在多步 \(\chi^2\) 能量/KL 约束下设计隐蔽攻击；Lemma 3、Theorem 1 给受攻误差协方差递推和下界，优化可转为一系列凸问题，Theorem 2 给 piecewise-constant 次优策略（pp.4546–4549）。攻击者拥有创新包并能线性混合历史和当前 innovation，这比“只能选择已发送的历史 estimate 包”更强。

Ge et al., IEEE TCyb (2026), DOI 10.1109/TCYB.2026.3721072，PDF 摘要、模型和定理部分已读：历史 innovation 矩阵、拓扑 block-diagonal 约束、\(\chi^2\)/KL 隐蔽性和 PGD/凸松弛攻击设计。它说明历史驱动的隐蔽攻击已有成熟建模，但不直接提供接收端防御或 Yang 缓存 MSE 保证。

## 6. 事件触发、时间信息和序贯检测

### 6.1 Mustafa et al. 2021：事件触发 DKF 的直接安全竞争

Mustafa, Mazouchi & Modares, *Secure Event-Triggered Distributed Kalman Filters for State Estimation over Wireless Sensor Networks*, arXiv:1901.06746v4 (23 Nov. 2021)，本地作者预印本全文。其系统在 PDF pp.2–4 式(1)–(7)中采用共同状态、各传感器量测和事件触发预测；Assumption 3 要求集体可观而允许单个节点不可观。事件触发变量决定发送当前先验估计还是使用上一发送值外推。

该文明确分析两种攻击：攻击者可利用量测和最近发送先验估计制造 **non-triggering misbehavior**，使节点停止发送；也可制造 **continuous-triggering misbehavior**，使事件触发退化为持续通信。PDF pp.5–6 Definition 2–7、Theorem 2–3 给出相应攻击构造；构造需要窃听实际量测、图结构和最近发送先验估计。它不是本项目“只能选择真实历史邻居 estimate 包”的同一权限，但已覆盖事件机制被攻击利用的核心风险。

检测方面，PDF pp.7–9 式(30)–(42)、Theorem 4–5 用 k-nearest-neighbor 估计创新分布的 KL 散度，在滑动窗口内检测传感器攻击和具体通信链路攻击；Algorithm 2 明确以邻居估计创新与本地名义创新的散度定位链路。防御方面，pp.9–11 式(43)–(48)使用 meta-Bayesian confidence/trust：

\[
\beta_i(k+1)=\beta_i(k)+\kappa_1\chi_i(k),\qquad
\sigma_{ij}(k+1)=\sigma_{ij}(k)+\kappa_2\theta_{ij}(k),
\]

并将其写入事件触发 DKF 的量测和邻居融合项。Theorem 6（PDF pp.11–12）在集体可观、诚实邻居数量和统一界条件下给出误差有界性。

**排重影响。** 事件触发、攻击诱导的触发异常、滑动窗口分布统计、链路定位和历史 trust 恢复已经在同一类分布式 Kalman 框架中组合出现。该文的攻击需要更强的窃听/篡改权限，且预印本不是出版社最终版；但它足以否定“把发送间隔或事件信息加入残差，再配一个 trust 融合器”作为独立新意。当前项目若研究固定外生间歇通信下的合法历史包 Replay，必须明确解决的是不同攻击权限和不同可观测对象，而不是重新命名该组合。

Tunga et al., ACC 2018，PDF pp.1752–1755：稳态 Kalman 残差 \(r_k\) 在健康时为 Gaussian，静态 \(\chi^2\) 统计 \(z_k=r_k^T\Sigma^{-1}r_k\)，CUSUM 更新为 \(S_k=\max(0,S_{k-1}+z_k-b)\)。windowed \(\chi^2\) 将多个 \(z_k\) 相加，但窗口重叠引入相关性；Theorem 1 和后续命题给窗口误报调参及零报警攻击造成的稳态偏差边界。它是“窗口统计+序贯检测”的直接竞争，而非缓存 episode 统计的空白。

Qiu et al., TIE 2019，PDF章节与公式已读：触发误差被显式并入故障检测残差/H∞-LMI阈值；它处理事件触发造成的阈值变化，但对象是故障诊断残差，不能直接当作链路完整性定理。

Liang & Liu, IEEE TIM 72 (2023) 3520111, DOI 10.1109/TIM.2022.3216674，PDF pp.3520111-2、式(11)–(15)、(20)–(30)：每个 agent 的事件触发 ZOH，接收端用 UIO 估计邻居并以相邻残差检测攻击/故障；Theorem 1 是 UIO 存在的秩/可检测条件，Theorem 2 设计残差解耦器，式(28)–(30)给 RMS 阈值。该方法依赖物理耦合模型和邻居测量/状态输出，攻击对象是连续 agent 通信信号，不是共同状态的 Yang 缓存；它仍说明“事件触发+邻居残差检测”已有直接先例。

Qian et al., 2023 研究事件触发条件期望估计；其贡献是保持 Gaussian/条件期望结构和通信效率，不是安全检测器。把不规则到达间隔纳入残差属于标准模型适配，不能直接算新颖性。

## 7. 其他强竞争与理论边界

- Yu et al., IEEE SPL 32 (2025) 1930–1934，式(2)–(4)和 Lemma 1：反射攻击使邻居差二次统计量不变；它要求更强的实时攻击权限，说明单一 spatial residual 不能保证安全。
- Zhang & Yang 2026 JFI，PDF pp.3–8 式(3)–(7)、Theorems 1–4：交换邻居 residual，windowed \(\chi^2\)，并讨论实时 residual attacker 与 watermark；额外残差消息和秘密种子必须算作资源。
- Wang et al. 2026 TASE，PDF pp.3–8：堆叠多拍局部输出，adaptive saturation 抑制稀疏 sensor attack；其 local sparse-observability 条件不等同单链路 estimate attack。
- Fawzi et al. 2014、Pasqualetti et al. 2013 给 sparse-observability/zero-dynamics 基础，但攻击者权限为连续输入或传感器错误，不是有限历史包选取。

## 8. 主动攻击线的判断

**已解决/已有工具：** residual/innovation 检测、windowed chi-square、CUSUM、随机保护、K-means trust、协方差交集、watermark、历史创新攻击优化、事件触发残差。

**可研究但未被证明的新问题：** 在没有可信序号、只有固定外生发送机会和真实历史 estimate 包的条件下，如何对“合法历史包选择空间”作可识别性和最坏闭环损失证书；但项目 G2 已显示简单 Replay 威胁成立而尚未找到稳定的防御增量，不能把问题直接写成创新。

证据：上述直接论文为 FULLTEXT；可识别性判断为 DERIVED/OPEN，G2结果另见既有报告。
