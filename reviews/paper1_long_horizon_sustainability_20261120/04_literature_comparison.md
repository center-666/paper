# 长期隐蔽攻击近邻：定向全文检查

日期2026-11-20；可追溯题录、获取地址和文件哈希见literature_sources.json。web.run多次未返回可用结果，因此随后读取官方机构仓储和Crossref的出版社登记数据；不将检索失败记成“无竞争文献”。

## Zhang–Shang–Wang–Liu，TAC 2026：取得机构仓储全文

题名：Remote State Estimation Under Stochastic Stealthy Attacks: Short-Term Optimization and Long-Term Convergence Analysis。DOI 10.1109/TAC.2026.3672354；出版社登记TAC 71(8):5382–5396。Brunel仓储记录citation_date为2026-03-09，Crossref卷期日期为2026年8月，分别记录，不混为同一出版时间。读取仓储15页“FINAL VERSION”，PDF页码为本报告定位。

本轮核查PDF pp.2–4模型、Assumptions 1–2与式(5)–(14)，pp.5–6 Theorem 1及攻击优化，pp.6–9 Theorems 2–3及收敛推论。未从头认证其所有证明。文本提取器有矢量路径警告，但正文公式、假设和定理可提取；第三方PDF和全文不加入仓库。

|项目|原文事实及定位|本研究的差别|
|---|---|---|
|发送/随机性|p.3每时刻发送量测；gamma_k是独立Bernoulli的攻击成功指示，式(5)–(6)|本研究gamma是依据真实量测与实际反馈中心生成的可信随机发送位，不能将两者重命名为同一权限|
|估计器|p.3稳态Kalman滤波器，固定增益Kbar|本研究有发送/静默两种信息更新和事件相关协方差标签|
|攻击与隐蔽|p.4式(10)线性创新变换加高斯白噪声；式(13)–(14)指定创新分布KL约束|本研究发送后逐路径有界载荷修改，约束整个事件+预测码前缀的联合TV；不等同单拍创新KL|
|停止攻击|p.6 Theorem 2，有限时间后停止的攻击使先验误差协方差回归正常稳态|停止注入后衰减并非新认识；本轮需额外区分条件偏差收缩与同码维持|
|持续攻击|pp.7–8 Definition 1、式(36)–(37)，有界非负一步协方差增量，Theorem 3针对恒定增量的算子固定点/收敛等价条件|本轮A=1见证通过真实发送时修复/重注入、静默时格不变，保持整个码/事件路径不变；不是固定攻击成功率的稳态算子|
|阈值|p.9相关推论给攻击成功率的必要/充分/等价收敛条件|本轮没有通用攻击成功率阈值，也不能以格内构造声称解决原文更广的系统问题|

原文已覆盖短期攻击优化、有限攻击后恢复和持续随机攻击长期收敛/发散。因此这些主题不可单独作为创新。其给定模型定理不能直接替换本轮的峰值权限、反馈量化、静默操作限制和整段记录TV问题；但“不同条件”也不等于新颖性已经通过。需把潜在增量限定在具体协议下的时间一致损伤界和持续路径隐蔽构造。

## Li–Xue–Zhao–Guo，TSIPN 2026：仅核到题录，全文OPEN

Crossref出版社登记确认：Remote State Estimation With Quantized Communication Against Markov Tampering Attack，Mengqi Li、Wenchao Xue、Yanlong Zhao、Jin Guo，IEEE Transactions on Signal and Information Processing over Networks，12:452–463，DOI 10.1109/TSIPN.2026.3672342。

不能把这篇误当成既有已读的Li–Hu–Guo IJRNC或Ad Hoc Networks文章。本次尝试登记PDF地址得到HTTP 200但内容是HTML，不是论文PDF；尚未获得能逐式核对的全文。用户指出的马尔可夫攻击、补偿、调度等内容作为待核线索，不能在本轮凭题名证实其全部定理，也不能宣称其没有覆盖本结果。

## 新颖性裁决

**OPEN。** 一篇直接长期近邻已全文定位，另一篇量化Markov近邻仍缺全文。未给出全面检索或全球不存在等价结论的证明。归一化滤波收缩、量化格不变性、分部积分均是已有工具；只有完整的信息权限—全前缀同律—持续真实损伤结论才是可评估的候选贡献。不得以尚缺全文为原创性证据。
