# P5.4来源版本核对：Badr、Dolk、Lu与Sun

日期：2026-11-18。第三方PDF不复制进Git；本文件保存版本、入口、页码和哈希，便于审阅者在Zotero或公开链接中复核。

## Badr《Layered Constructions for Low-Delay Streaming Codes》

### 2013 arXiv作者稿

实际核读文件是Zotero条目`QM8GAQDM`目录中的32页PDF，而不是文件名中的“2017”。arXiv API只确认`1308.3827v1`，提交日期为2013-08-18。PDF第2–3页定义$C(N,B,W)$、Definition 1、Theorem 1–2；PDF第28页Appendix A Proposition 4式(82)–(83)给出

$$
\frac{R}{1-R}c_T+d_T\le T+1+\frac1{1-R},
\qquad
\frac{R}{1-R}c_T+d_T\ge T+\frac1{1-R}
$$

（后式为存在性方向）。文件SHA256：`f424c5b8163bfc2e6d0ee5c621d49a5278c1a8c00793f11b25e4f8a20d3974e4`。

### 2015作者机构修订稿

从作者机构入口取得的32页版本：<https://www.comm.utoronto.ca/~akhisti/layered-jrnl.pdf>。PDF元数据创建时间为2015-04-03，标题仍包含作者本地DVI路径；它不是IEEE最终排版版。PDF第2页保留同一$C(N,B,W)$定义；PDF第4页把列距离/列跨度结果提升为正文Proposition 1式(3)–(4)；PDF第4–5页Theorem 3式(8)–(10)明确列出$T=b$的两个$B'$分支。SHA256：`743da8a6dd1e45ef1f9c06a9a5378968fe419a8739685b29fa2c32af96dc8755`。

**DERIVED — 不能把分段重写当成新定理。** 2013稿PDF4式(6)第一分支允许 $T\ge b$。代入 $T=b>0$ 后，条件化为 $B'\le M/2$，容量化为 $1/2$；第三分支覆盖 $B'>M/2$。2015稿PDF4–5式(9)–(10)把该情形单列。已核范围内两式等价，修订属于呈现和编号变化，没有确认到相应数学结果变化。$T=b=0$ 的退化表述不在本次比较结论内。

### 2017 IEEE期刊版

DOI为<https://doi.org/10.1109/TIT.2016.2618924>，Crossref元数据为IEEE Transactions on Information Theory 63(1), 111–141 (2017)，IEEE文档号7593328。可继续尝试[IEEE文档页](https://ieeexplore.ieee.org/document/7593328)、[IEEE stamp PDF](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=7593328)和[IEEE PDF路径](https://ieeexplore.ieee.org/ielx7/18/7792231/07593328.pdf)。IEEE Xplore最终VOR本轮未成功取得，因此：

- 2013 v1与2015作者稿的窗口模型映射可以逐式核对；
- 作者稿显示了正文位置和容量分段写法的重排，已核边界公式等价；
- 不能把作者稿称为VOR，也不能声称期刊版逐页完全一致；
- 对ACK-V1的T1，只需要窗口集合约束，作者稿与V1已足以支持“信道条件等价、ACK表述为推论”的判断。

## Dolk博士论文

文件：`20171106_Dolk.pdf`，301页，SHA256 `ae5fa63945907d34755010a589816618cd0235a268e309048b4adf034395f9ca`。第5章书内页107–129对应PDF页123–145。Assumption 5.1在PDF128；Condition 5.2式(5.27)在PDF135；Theorem 5.1式(5.30)–(5.31)在PDF136。该章处理连续失败数、事件间隔和稳定性/性能，不定义ACK-V1的历史时间戳集合、硬滑窗总阻断或固定截止首成功次数。因此标记为ANALOGOUS，且仅针对已核读第5章。

## Lu–Lin–Yang 2026

实际取得16页正文，SHA256 `96ee7eaa669f0cfb55aaf71ff73d9c18caed1e1d056616bfb1a0d37ddaed160a`。PDF第5页式(17)–(19)是模式相关Bernoulli接收模型；第6–7页式(22)、(24)–(26)是Fisher信息和期望协方差下界；第7页式(28)–(29)是概率预测；第8页式(31)与Theorem 1是单步信息收益排序。它不是硬滑窗路径预算，也不是固定截止minimax。

## Sun 2026

Zotero接受稿16页，SHA256 `16444606ecd7328958dc6846187ff99275f09b64fbe08df0576957ec20dc4206`。PDF第3页是本地KF、集中调度器和可靠ACK模型；PDF第8页式(31)–(32)给AoI状态转移，第8页式(34)–(37)给无限时域平均协方差成本和Bellman方程；PDF第9页Theorem 3给切换结构。该结果说明一般ACK/AoI/Bellman调度已有直接近邻，但其概率接收、集中多传感器、长期平均MSE目标与ACK-V1的硬滑窗、单次截止、路径wise首成功目标不同。
