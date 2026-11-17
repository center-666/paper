# P5 全文补充：Dolk 第5章与 Lu 2026

**FACT。** 本文件追加 P5 来源和逐式对照，不覆盖 ../10—13 号历史报告。
P5当时未取得两份可读正文是历史获取状态；本轮用户补充下载后关闭这两项来源缺口，不据此声称所有版本差异及全部文献排重已完成。

## 1. 来源、版本和页码

| 来源 | 本轮实际文件 | 版本、公开入口、摘要 |
|---|---|---|
| Victor S. Dolk, Resource-aware and Resilient Control: with Applications to Cooperative Driving, TU/e博士论文, 2017 | C:\Users\zhongxin\Zotero\storage\SZQNVNM6\20171106_Dolk.pdf | 301页；[官方PDF](https://pure.tue.nl/ws/files/79595404/20171106_Dolk.pdf)；[机构题录](https://research.tue.nl/en/publications/d0d45c97-cdef-4070-a591-7f8c6657d70d)。本轮不猜测论文DOI。SHA256：ae5fa63945907d34755010a589816618cd0235a268e309048b4adf034395f9ca |
| Jie Lu, Wenhao Lin, Chao Yang, Sequential Information Fusion for Resilient Estimation: Dynamic Observation Scheduling against Intermittent DoS Attacks, CJIF 3(1):46–61, 2026 | C:\Users\zhongxin\Downloads\CJIF-O9ZqfzdqpFlWypz6Y.pdf | 正式正文16页，1,791,729字节；[DOI](https://doi.org/10.62762/CJIF.2025.922221)，[出版社PDF入口](https://www.icck.org/filebob/uploads/storage/CJIF_O9ZqfzdqpFlWypz6Y.pdf)。SHA256：96ee7eaa669f0cfb55aaf71ff73d9c18caed1e1d056616bfb1a0d37ddaed160a |

**FACT。** Dolk第5章书内107—129页对应物理PDF123—145页，不可把书内页号当PDF索引。Lu的PDF第p页对应期刊45+p页。Lu的Zotero PU33H6JI附件为网页快照，本轮不声称正式PDF已入库。出版社入口再次自动获取时仍出现网页打印版本；最终审读依据是上述用户本地16页文件。第三方原文均未加入Git。

## 2. Dolk：模型、公式与保证

**FACT。** Assumption5.1（PDF128/书112）限定上次成功以后连续尝试失败数 δ≤δ_max；成功到达才刷新控制器数据，失败保持，式(5.6)允许一般保持动力学。§5.4（PDF131—133/书115—117）用时钟τ、连续失败计数δ和尝试计数κ建立混合系统；§5.5明确使用ACK。

**FACT。** Condition5.2（PDF135/书119）式(5.27)：
\[
(\delta_{\max}+1)\tau_{\rm miet}<T(\gamma,L).
\]
这里 L 是 Condition5.1 式(5.24) 中误差增长常数，**不是本项目物理窗口长度**。
Theorem5.1（PDF136/书120）在Condition5.1、5.2和初始化集合下，以
\[
\Psi(o,\eta)=
\begin{cases}
\varrho(y)-\chi(\eta),&\tau\le\tau_{\rm miet},\\
\varrho(y)-\bar\gamma(\delta)W^2(e)-\chi(\eta),&\tau>\tau_{\rm miet},
\end{cases}
\qquad
\eta_0(o)=\gamma\phi((\delta+1)\tau_{\rm miet})W^2(e)
\]
即式(5.30)、(5.31)，保证UGAS、扰动下 L_p 增益≤θ和正MIET。Fig5.4（PDF145/书129）展示MANSD与平均/最小事件间隔关系。不能把“ACK失败记忆与稳定性—资源权衡”称为本项目原创。

**DERIVED：约束不能互换。** 取本项目 B=1,L=3，尝试仅在1、4、7、…发生，每次均失败仍满足硬滑窗预算，却有无限连续尝试失败；因此该预算不推出有限MANSD。反向取尝试每拍发生，失败/成功交替，MANSD=1成立，但长度3窗口可有2次失败，不满足(B,L)=(1,3)。只有额外限制尝试间隔，才能建立某些转换。

**DERIVED：逐项结论。** 该章没有用本项目的 H_k、U_k(t)、固定D或全失败机会S定义首成功minimax。其定理不能仅通过令δ_max=B得到T2/T3。整体关系 **ANALOGOUS**；“本章未覆盖相同T2/T3陈述”仅限本章已审读公式及证明，不是全球新颖性证据。

## 3. Lu：概率窗口并非硬预算窗口

**FACT。** §2.3（PDF5/期刊50）式(17)—(19)为有限攻击模式、模式Markov转移和各子窗口成功概率
\[
\gamma_k(j)\sim{\rm Bernoulli}(1-q_j^{(i)}),\quad p_k(j)=1-q_j^{(i)}.
\]
Assumption1规定条件Bernoulli独立、子量测噪声独立及仅丢失不篡改；Remark2明确对依赖完整历史交互的自适应攻击者存在局限。模式混合后的跨时相关性不能简单当作独立丢包。

**FACT。** PDF6—7/期刊51—52：Proposition1式(22)、(24)—(26)给
\[
I_j=C_j^\top R_j^{-1}C_j,\qquad d_j={\rm tr}(I_j).
\]
Lemma1给定先验的信息形式下
\[
E[P_{k|k}]\succeq
\left(Y_{k|k-1}+\sum_jp_k(j)I_j\right)^{-1}.
\]
这是矩阵求逆凸性产生的**下界**。它不是本项目想要的估计误差上界，不能从减小该下界推出实际MSE必减。

**FACT。** PDF7/期刊52式(28)、(29)：
\[
\hat p_{k+1}(j)=\sum_{i=0}^{L-1}\frac{r^i}{\sum_{\ell=0}^{L-1}r^\ell}\gamma_{k-i}(j),
\qquad\hat p_{k+1}(j)\approx p_{k+1}(j).
\]
L是预测记忆长度；近似是算法依据，不是“每个长度L的物理窗口最多B次阻断”的逐路径保证。

**FACT。** PDF8/期刊53式(31)、Theorem1最大化
\[
J(\pi)=\sum_j\hat p(\pi(j))d_j.
\]
窗口可靠性不随所分配载荷改变时，交换逆序对的增益为
\[
(\hat p_v-\hat p_u)(d_u-d_v)>0,
\]
因此同序匹配最大化该单步标量目标。相等权重时允许并列，不能据此推唯一排序。
**DERIVED。** 这个证明没有最小化真实MSE、固定截止任务最坏发送次数或自适应硬预算攻击风险；不能把该页末尾对“best possible estimator performance”的宽泛表述当作上述不同目标已被证明。

## 4. 统一排重表（本轮新增来源）

| ACK-V1结果 | Dolk第5章 | Lu正式正文 | 具体推导/不能映射之处 |
|---|---|---|---|
| T1：max_t[U_k(t)+N_S(t)]>B | NOT COVERED；整体ANALOGOUS | NOT COVERED；整体ANALOGOUS | Dolk假设5.1限制连续尝试失败而非H∪S的物理窗口计数；Lu式(17)—(19)允许有概率出现超过任意固定B的失败，未施加此路径约束 |
| T2：所有安全确定性因果策略的首成功最坏次数 | NOT COVERED | NOT COVERED | Dolk Thm5.1优化/保证稳定性与间隔，未定义N_through；Lu Thm1在有限排列类上优化J，不是等待/尝试策略博弈 |
| T3：m(s)、s_cost、s_safe | NOT COVERED | NOT COVERED | Dolk式(5.27)是统一MIET条件，无失败时间戳过期曲线；Lu式(28)是加权概率预测，无固定D前强制成功 |
| ACK、历史失败记忆与资源性能折中 | ANALOGOUS，已明确研究 | ANALOGOUS，使用历史接收结果 | 不能据应用措辞或“使用记忆”认定新颖 |
| 本轮原规则可达分类与成本中性实现 | NOT COVERED于所核章节 | NOT COVERED于所核全文 | 两篇没有本项目低偏差锚点规则，不能直接得到B≥2,L≥B+4分类；但本轮结果仍可能是既有T3的专门化推论 |

**DERIVED / 定位。** T1继续降为基础引理；T2保留条件化单任务命题；T3及本轮可达分类可作为理论链候选，创新风险仍高。关闭两项OPEN不会自动使P6或论文通过。既有P5的其他作者版/期刊版差异、旧实验完整源码溯源等OPEN仍保留；不把此次二篇补读当全量排重完成。
