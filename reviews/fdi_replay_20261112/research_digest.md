# 精华报告：FDI / Replay分布式滤波的研究问题筛选

日期：2026-11-12。文献精读底稿有28篇全文，方法比较与公式定位见[完整版](literature_reading_notes.md)；已有实验边界见[项目证据](project_evidence.md)。

## 结论

**目前值得先用一轮小验证筛的，是“同一邻居estimate缓存episode内的持续FDI风险控制”；但它尚未通过新颖性门槛，且不是已成立的论文贡献。** 竞争文献里已有随机残差保护、窗口χ²/CUSUM、事件触发UIO、多跳子空间信任及Replay检测；本候选唯一区别可以检验的是：多个新本地量测在同一邻居估计缓存存续期间反复观察一个共享、未知估计偏差，episode内残差因共享cache error相关，应该怎样形成可控首次误隔离率的统计证据，以及它在同一发送机会/误隔离水平下是否超过窗口/CUSUM基线。这个结构差异的理论与基准差异都还没有建立。

更重要的是，已有序贯比较给出完整场景单元仅1/4通过；低幅FDI、匹配Replay及主链部分可观测压力没有稳定优势。所以最多先做重新定义后的最小复核；若与Liang 2023 UIO结果直接重合，或简单GLS窗口不能在equal-risk下胜过强基线，就停止这条贡献，不再叠模块。

## 为什么不是恢复原IR-TCF标题

原方向是状态链路空间/时间残差、按间隔标定、可信记忆及clip融合。直接技术组件已有先例：Zhou 2022状态残差χ²与随机保护；Güzey 2026完整时序trust/似然/滞回/Replay保持；Nozal 2022多跳子空间信任与恢复；Peng 2025时空参考与统计核；Tunga 2018 windowed χ²/CUSUM；Wang 2026分布式自适应饱和。项目同骨架间隔尾部对9项主比较0项过，reference恢复对6项0项过。该标题现在没有独立方法支撑。

## 最强的直接竞争方式

1. Zhou 2022: 本地measurement对received estimate残差，加χ²滑窗；零空间攻击条件及接收端随机exp门控。它必须成为同权限主基准。
2. Liang–Liu 2023: event-triggered MAS，UIO对邻居ZOH输出作连续attack diagnosis，残差明确计通信误差；模型并非多传感器共同估一个x，但对episode detector极近。
3. Tunga 2018: 静态χ²、CUSUM、windowed χ²，目标FAR可解析设定且分析zero-alarm attack。简单相关白化/GLS不应跳过它。
4. Güzey–Güzey 2026: 中心化SISMF tracking，NIS + LLR + forgetting + hysteresis + hold-last bearing Replay + WLS/IRLS，50 Monte Carlo及消融。架构不同，但历史trust不是新点。
5. Yu 2025: 反射状态包精确保持邻居差χ²统计；动态编码缓解。攻击者信息比历史packet-only强。
6. Huang 2024 / Xing 2025 / Ge 2026: measurement片段Replay或历史innovation隐蔽攻击优化，字段不同，揭示时间与历史同时帮助攻击者。
7. Mitra AoI 2022 / Su Replay 2022: AoI可伪造；Su的100% Replay检测依赖不篡改标签，跟当前无trusted freshness攻击权限不等价。

具体逐篇页码、公式号、假设、实验与“不可以从对方直接推出什么”，见[方法级阅读笔记](literature_reading_notes.md)。

## 最小筛选计划

当前不必写新检测器。先正式化cache-episode联合统计模型：接收时刻r收到\(\tilde m_j(r)\)，后续年龄a的本地残差\(r_a=y_i(r+a)-H_iA^a\tilde m_j(r)\)。如果条件于发送/接收历史后的缓存估计误差q_r为Gaussian，其joint covariance有共同P_q项和跨时过程噪声项；但触发选择可能改变q_r的条件分布，所以不能默认Gaussian或独立。先用真实事件协议核查联合分布，再比较single χ²、Zhou保护、相关window/GLS、跨包CUSUM。若用episode-max门限，只能说在独立tune样本上经验匹配目标episode-FPR，再在audit/test报告偏差与不确定性，不能说distribution-free控制。用新种子测试persistent step、half/low step、固定delay Replay和时隔匹配历史Replay。所有方法共用发送机会；单独报告闭环成本。

**停止条件**：匹配FPR/通信机会后没有可重复的receiver MSE或检测延迟收益；优势只在强step且在简单CUSUM/GLS后消失；rank-deficient主链仍没有可验证信息；或Liang等工作能直接覆盖相同条件。满足其一就不把它立为主贡献。

**次选但不立题：**从每条攻击链路已经实际截获的历史估计包里自适应选Replay payload。项目旧字典探针只用冻结健康sender stream算评分/一步影响proxy，没有闭环MSE证据。该问题可做攻击模型门槛，但单靠攻击选择器未必形成防御论文。

## 下载说明

本轮助手新增成功下载论文PDF **0篇**。Yu SPL 2025和Xing TIFS 2025是用户刚放入Zotero的全文；已只读复制、提取和核对SHA-256。其他全文为此前本地/Zotero来源。未修改Zotero数据库，未提交第三方PDF或全文。
