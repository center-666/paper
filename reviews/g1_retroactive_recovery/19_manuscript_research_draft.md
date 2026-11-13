# 间歇通信下分布式状态估计的链路重放攻击传播分析与主动恢复方法

> **研究草稿，尚不具备投稿条件。** 以下稿件忠实记录当前模型和结果，不将标准线性传播与GLS称为原创定理，不声称优于同信息全网影子基线。实际异步修正通信、强竞争方法的忠实性能对照和论文创新性尚未通过验收。作者、单位及参考文献格式待最终核对。

## 摘要

针对间歇通信分布式估计中历史估计包被重放后可能产生的持续污染，研究固定外生通信日程下单条有向链路的一次历史包替换。采用Yang型估计器，并将节点估计与接收缓存组成增广状态，利用固定模式的攻击响应描述恶意包退出缓存后残余污染的传播。接收端依据本地量测创新和实际接收记录，对历史候选包计算广义最小二乘分数及载荷差估计；在理想同步修正通信下，节点分别回写自身估计和入边缓存，并继续递推。分析指出：当事件归责和载荷差估计均准确时，回写可恢复配对的名义增广状态；估计不准确时，其真实均方误差包含与名义误差的交叉项。固定模式下，联合回写与采用相同估计量及响应的全网影子输出具有相同的估计轨迹。五节点、100个独立测试种子的基准Replay场景中，回写和影子输出的接收节点恢复窗均方误差均为0.2534，未防护估计为1.0077；100个正常样本中有10次误报警。实验同时暴露出错误归责、理想通信假设和强竞争基线不足等限制。结果说明该机制可在所设条件下恢复内部状态，但尚不能证明其优于全网影子方法或具有足够独立创新。

**关键词：** 分布式状态估计；重放攻击；间歇通信；缓存污染；估计恢复；广义最小二乘

## Abstract

This study examines propagation and recovery after a single historical estimate packet is replayed on one directed link of a distributed estimator under a fixed intermittent communication schedule. A Yang-form estimator is represented with an augmented state containing node estimates and received-packet caches. A receiver uses local innovations and reception records to score candidate historical packets and estimate the payload offset by generalized least squares. Under ideal synchronized control communication, the estimated influence is written back to node states and incoming caches. Conditional identities relate recovery error to offset estimation error, including its cross term with nominal estimation error. Under the same fixed linear mode, joint write-back and full-network shadow correction using the same estimate have identical output trajectories. In the five-node, 100-seed baseline experiment, their receiver recovery-window mean squared errors are both 0.2534, compared with 1.0077 for the unprotected estimator; ten alarms occur in 100 clean trials. The results demonstrate conditional internal recovery but do not establish an MSE advantage over the shadow baseline or a validated contribution over direct competing methods.

**Key words:** distributed state estimation; replay attack; intermittent communication; cache contamination; recovery

## 1 引言

分布式状态估计通过邻居交换局部估计改善网络整体估计性能。Yang等[1]研究了随机传感器激活下的分布式状态估计；其原始随机激活模型与本文采用的固定间歇发送、每步本地量测和缓存外推并不相同。现有研究已分析邻居信息遭受虚假数据注入时的检测和保护，例如Yang等[2]及Zhou等[3]。历史数据重放同样可能破坏估计，例如Huang等[4]研究测量Replay，Xing等[5]研究利用历史创新数据的隐蔽攻击；这些攻击入口和权限与本文的单次邻居估计包替换不同。

攻击结束或恶意包被新包覆盖后，受影响节点估计可能已经通过后续通信传到其他节点。因此，仅删除当前可疑缓存未必能消除历史污染。另一方面，利用后续数据识别或修正攻击影响并非新问题。Deghat等[6]在连续时间网络中构造攻击输入跟踪器并修正观测器误差；其原模型和辅助网络信息与本文离散缓存系统不同，但不能仅凭模型名称差异宣称本文方法新颖。

本文在一个限定的五节点固定日程模型中，整理单次Replay污染传播、接收端局部GLS估计和状态—缓存联合回写的实现与实验。分析同时给出回写与全网影子输出在固定线性模式下的等价关系。本文没有建立相对直接竞争方法的普遍优势；实验中的理想同步控制通信亦不是现有间歇网络已具备的能力。

## 2 系统与攻击模型

### 2.1 系统和估计器

离散系统及节点i量测为

$$x_{k+1}=Ax_k+w_k,\qquad y_i(k)=H_i x_k+v_i(k). \tag{1}$$

以 $\hat x_i(k)$ 表示节点i第k拍开始时的估计，$c_{ji}(k)$ 为接收端i在第k拍收包处理后的边 $j\to i$ 原始缓存，$\tau_{ji}(k)$ 为其最近接收时间。根据固定日程，如j在k发送，接收端用实际收到的载荷替换缓存；否则保持原载荷。对齐值为

$$\bar c_{ji}(k)=A^{k-\tau_{ji}(k)}c_{ji}(k). \tag{2}$$

发送当拍的新包年龄为0，立即用于第k拍更新。项目采用的Yang型递推为

$$\begin{aligned}
\hat x_i(k+1)={}&A\hat x_i(k)+K_i(k)[y_i(k)-H_i\hat x_i(k)]\\
&+\epsilon A\sum_{j\in\mathcal N_i}[\bar c_{ji}(k)-\hat x_i(k)].
\end{aligned}\tag{3}$$

$K_i(k)$ 为依据项目全通信名义协方差递推生成的增益；本文未证明它是间歇缓存模型的最优增益。不存在另加的Kalman预测步骤。

### 2.2 单次历史包Replay

在时刻r的一次实际发送中，攻击者仅替换一条有向链路 $e^*=j\to i$ 的载荷，所替换内容是之前已经实际发送并被截获的历史估计包；其他通信不再被攻击者篡改。记当次被替换载荷相对正常当前载荷的差为 $a$。$a$ 可与系统噪声相关，且只用于建模和离线oracle评价，不作为实际恢复器输入。攻击者不修改本地量测，不读取未来量测；接收端不默认能获得未篡改的当次原始包。

配对健康和攻击运行具有同一初始条件、噪声、本地量测、固定发送日程与增益。后续发送没有再次受到攻击者篡改，并不意味着其发送端估计已不含网络反馈污染。

### 2.3 增广状态与响应

令 $z_k$ 堆叠第k拍开始时所有节点估计和上一拍收包处理后的所有原始缓存。固定日程下，估计与缓存更新为线性时变递推。记事件 $(e,r)$ 的增广状态响应为 $T_k^{e,r}$，则对单次实际Replay逐样本有

$$z_k^a-z_k^0=T_k^{e^*,r}a,\quad
T_r^{e^*,r}=0,\quad T_{r+1}^{e^*,r}=B_r,\quad
T_{k+1}^{e^*,r}=F_kT_k^{e^*,r}. \tag{4}$$

矩阵 $F_k,B_r$ 由公开系统、增益、网络及发送日程确定，包含缓存更换和年龄外推；它们的具体构造及此前固定模式验证见项目P0记录。式(4)属于标准线性系统传播关系，不单独构成新理论。

## 3 接收记录归责及联合回写

### 3.1 基于局部创新的候选事件评价

设接收端i在预设决策时刻d拥有本地创新序列和入边实际接收记录。从固定窗口内的接收事件构造候选集合 $\mathcal C_i$。把窗口局部创新堆叠为 $v$；对候选 $(e,r)$，由公开模型和日程计算其创新响应 $J_{e,r}$，并用独立健康训练数据估计均值 $\mu$ 与正则化协方差 $V$。采用

$$\hat a_{e,r}=(J_{e,r}^{\mathsf T}V^{-1}J_{e,r})^\dagger J_{e,r}^{\mathsf T}V^{-1}(v-\mu), \tag{5}$$

$$s_{e,r}=\hat a_{e,r}^{\mathsf T}J_{e,r}^{\mathsf T}V^{-1}J_{e,r}\hat a_{e,r}. \tag{6}$$

以 $s_{\max}=\max_{(e,r)\in\mathcal C_i}s_{e,r}$ 和独立正常校准集上最大分数的经验分位数判断是否报警；报警时选择最大分数候选。未报警时不回写。固定决策时刻及候选窗口是本实验的局限；正常样本和候选数量有限，经验阈值不是对任意时刻误报概率的保证。

### 3.2 状态与缓存回写

设归责结果为 $(\tilde e,\tilde r)$，载荷差估计为 $\hat a$。在第d拍状态更新与接收缓存处理后，节点对自身估计和入边缓存分别减去对应的响应分量，即增广形式

$$z_{d+1}^{\rm rec}=z_{d+1}^{a}-T_{d+1}^{\tilde e,\tilde r}\hat a. \tag{7}$$

此后以修正后的内部状态和缓存继续式(3)，而非只修正显示输出。仿真中，接收端将事件编号、接收时刻、决策时刻及二维估计量发送给其余节点；网络树包含4次逐边传输，每条控制载荷21字节。实现假设两轮控制消息可靠地在下一主迭代前到达并同步回写，不含帧头、认证、重传、消息丢失及真实时延。

## 4 条件性分析

### 命题1：攻击传播

在式(1)—(4)及配对健康运行条件下，对任意满足单次Replay模型的随机载荷差 $a$，式(4)逐样本成立，不要求其与噪声独立。该命题继承固定线性系统的传播恒等式。

### 命题2：准确估计下的恢复

若归责正确、$\hat a=a$，且式(7)在全部节点状态及缓存上可靠同步执行，则 $z_{d+1}^{\rm rec}=z_{d+1}^{0}$。其后若两过程采用相同日程、输入及增益，且没有再次攻击，则所有 $k\ge d+1$ 都有 $z_k^{\rm rec}=z_k^0$。

证明：由命题1，$z_{d+1}^a=z_{d+1}^0+T_{d+1}^{e^*,r}a$；代入式(7)得当前增广状态相同。随后在同一线性递推下归纳即可。准确载荷差仅是oracle条件，实际GLS估计不保证准确。

### 命题3：估计偏差与真实MSE

归责正确时，令 $q=a-\hat a$，$P_i$ 为节点估计选择矩阵，$u_i(k)=P_iT_k^{e^*,r}q$，$e_i^0(k)=x_k-P_i z_k^0$。对 $k\ge d+1$，

$$z_k^{\rm rec}-z_k^0=T_k^{e^*,r}q,\qquad
J_i^{\rm rec}(k)-J_i^0(k)=\mathbb E\|u_i(k)\|^2-2\mathbb E[(e_i^0(k))^{\mathsf T}u_i(k)]. \tag{8}$$

若二阶矩有限，则

$$\sqrt{J_i^{\rm rec}(k)}\le\sqrt{J_i^0(k)}+
\|P_iT_k^{e^*,r}\|_2\sqrt{\mathbb E\|a-\hat a\|^2}. \tag{9}$$

式(8)的交叉项一般不能消去；式(9)为条件性有限时刻上界，不保证恢复后MSE不高于受攻击轨迹。若归责错误，残余污染为真实事件响应 $T_k^{e^*,r}a$ 与选中候选修正响应之差，不能用正确归责公式替代。

### 与影子输出的关系

定义全网影子输出 $z_k^{\rm sh}=z_k^a-T_k^{\tilde e,\tilde r}\hat a$。在式(7)的同步条件、固定日程及同一估计量下，线性递推给出 $z_k^{\rm rec}=z_k^{\rm sh}$。故两者节点输出和MSE逐样本相同。影子方法在当前实验中为离线全网输出，未实现网络分发；这一等价不证明两种实际部署的通信成本相同，也不否定回写内部缓存的功能差异。

单个已知事件、已知回写时刻的节点与缓存响应快照存储量为 $O((N+E)n^2)$；长度L的固定局部GLS窗口在线计算量为 $O(n^2L)$。这一计数不包括多候选响应表、离线协方差估计、节点协议或正常滤波器本身，实际占用与实现见项目资源记录。

## 5 数值实验

### 5.1 配置与对照

采用已有五节点双向环、二维状态，$A=\begin{bmatrix}1&0.1\\0&1.01\end{bmatrix}$，$Q=0.02I$，各节点 $R_i=0.05I$；节点测量矩阵分别为 $\operatorname{diag}(1,0.15)$、$\operatorname{diag}(0.15,1)$、$\operatorname{diag}(1,0.15)$、$\operatorname{diag}(0.15,1)$、$0.7I$，一致性系数 $\epsilon=0.08$。初始状态服从 $\mathcal N(0,I)$，各节点初始估计为0；过程噪声和各节点量测噪声分别为零均值高斯分布，协方差为 $Q$ 和 $R_i$，在时间、节点及初始状态之间独立。模拟每条独立seed轨迹使用相互独立的随机数。

基准gap为8，节点 $j$ 的发送日程满足 $k\bmod 8=j$，并在0时刻全部发送；攻击于200时刻替换0→1链路载荷为实际发送过的64步历史包；下一正常包在208到达，216决策，217—260为恢复评价窗。归责窗口为176—216，包含节点1的两条入边历史接收事件。训练64个seed、正常校准48个seed、最终测试100个新seed，三组互不重叠；在测试数据生成前冻结参数及校准结果。同一seed下各方法共享系统噪声及发送机会。结果为100个seed的均值与配对区间，非对所有系统和攻击策略的保证。

比较原Yang、报警后持续隔离、丢弃当前仍被判定的可疑缓存、全网离线GLS影子、联合回写以及已知真实攻击差的oracle。若被归责的历史包已经过期，丢包对当前缓存无操作，不做历史回滚。oracle只作名义恢复参考，不能视为所有方法真实MSE的必然下界。

### 5.2 基准性能与正常代价

|方法|接收节点恢复窗MSE|全网恢复窗MSE|
|---|---:|---:|
|原Yang|1.00771|0.43971|
|报警后隔离|1.21465|0.48069|
|丢弃当前可疑包|1.00771|0.43971|
|全网影子输出|0.25339|0.21405|
|联合状态与缓存回写|0.25339|0.21405|
|oracle名义恢复|0.25038|0.21253|

联合回写相对Yang的接收节点MSE配对均值差为−0.75432，95% t区间为[−0.96131,−0.54732]；多情形比较未做多重校正。与全网影子相比，两者逐样本状态最大差为 $3.42\times10^{-13}$，符合第4节的固定线性模式等价关系。结果不能作为联合回写优于该影子基线的证据。

100个Replay测试样本中91个报警、85个正确归责、6个错误归责，另有9个未报警。100个正常样本中10个报警，Wilson 95%区间为[5.52%,17.44%]。正常条件下联合回写相对Yang接收MSE配对差为−0.00152，95%区间[−0.00575,0.00270]，尚不能判定正常误修正代价为零。控制消息在攻击场景下的平均附加载荷为76.44字节/试验，正常场景为8.4字节/试验；真实通信开销和可靠性未测。

图1 基准场景接收节点恢复窗MSE及95%区间：[图文件](results/g1r_final_analysis_20261113_v1/main_mse.png)。

### 5.3 历史包年龄、幅值和通信间隔

固定gap8时，历史包年龄32、64、96步的联合回写接收MSE分别为0.25962、0.25339、0.25681；对应100个样本的报警数分别为80、91、92，正确归责数为69、85、88。历史包年龄同时改变载荷和自然攻击差，结果不能单独解释为年龄的因果效应。

按预注册规则，以基准场景离线获得的真实Replay载荷差模长进行观察性三等分。低幅组34个样本中25个报警、20个正确归责；中组33个均报警、32个正确归责；高组33个均报警且正确归责。没有对历史包数值缩放，不能将这一观察性分组视为受控幅值干预。

当gap取4、8、12且仍选第8个前序实际发送包时，对应实际包年龄为32、64、96步，决策时刻为208、216、224。联合回写接收MSE分别为0.24141、0.25339、0.33660。通信间隔、历史包年龄与检测延迟同时改变，不能将差异仅归因于通信间隔。

图2 历史包年龄及通信间隔对照：[图文件](results/g1r_final_analysis_20261113_v1/sensitivity_mse.png)。

### 5.4 局限性

实验只检验固定外生日程、固定判定时刻、单次实际历史包Replay及理想同步修正；没有检验闭环事件触发、网络控制报文的真实时延、丢失或伪造。正常误报和错误归责可能造成不必要的回写；接收端无法访问原始未篡改包或真实攻击差。强近邻Deghat方法尚未完成忠实离散缓存适配，不能声称本文优于该方法。当前理论主要为标准传播恒等式及条件性推论，缺乏经强基线支持的独立创新结论。

## 6 结论

在固定通信日程和理想同步修正条件下，将估计状态及缓存一并回写可以消除已估计的历史包传播分量，并使节点从修正后的内部状态继续运行。基准实验中，联合回写低于无保护Yang的恢复窗MSE，但与同信息全网影子输出等价；正常误报警及错误归责仍然存在。上述发现限制了将MSE收益归因于回写机制的可能性。是否以内部状态和缓存实际恢复作为有价值的工程目标，需要结合真实通信资源及直接竞争方法进一步评估。

## 参考文献（投稿前核对作者完整名单及格式）

[1] Yang W, Chen G, Wang X, Shi L. Stochastic sensor activation for distributed state estimation over a sensor network[J]. Automatica, 2014, 50(8): 2070–2076. DOI: 10.1016/j.automatica.2014.05.025.

[2] Yang W, Zhang Y, Chen G, Yang C, Shi L. Distributed filtering under false data injection attacks[J]. Automatica, 2019, 102: 34–44. DOI: 10.1016/j.automatica.2018.12.027.

[3] Zhou J, Yang W, Zhang H, Zheng W X, Xu Y, Tang Y. Security analysis and defense strategy of distributed filtering under false data injection attacks[J]. Automatica, 2022, 138: 110151. DOI: 10.1016/j.automatica.2021.110151.

[4] Huang J, Yang W, Ho D W C, Li F, Tang Y. Security analysis of distributed consensus filtering under replay attacks[J]. IEEE Transactions on Cybernetics, 2024, 54(6): 3526–3539. DOI: 10.1109/TCYB.2022.3209820.

[5] Xing J, Ye D, Li P. Stealthy attacks with historical data on distributed state estimation[J]. IEEE Transactions on Information Forensics and Security, 2025, 20: 4541–4550. DOI: 10.1109/TIFS.2025.3564063.

[6] Deghat M, Ugrinovskii V, Shames I, Langbort C. Detection and mitigation of biasing attacks on distributed estimation networks[J]. Automatica, 2019, 99: 369–381. DOI: 10.1016/j.automatica.2018.10.052.
