# 可信本地校准候选：范围与既有资产审计

审查日期：2026-11-19。工作分支 `trusted-local-calibration-preaudit`，审查基线 `9901785cf565e3bcfbe814080b04b997fd661377`。本轮新增的是立项前筛选，不改 Baseline-Y5 的模型、Yang 增益、配置、旧论文或旧结果。

## 候选问题

候选拟在接收节点并行运行只使用本地量测的参考滤波器：

```text
xbar_(i,k+1) = A xbar_(i,k) + Kloc_i (y_(i,k) − H_i xbar_(i,k))
u_(i,k)      = y_(i,k) − H_i xbar_(i,k)
r_(j,i,k)    = received_neighbor_estimate_(j→i,k) − xbar_(i,k)
```

用 `u_i` 的历史估计正常噪声尺度，用其标准化 `r_(j,i)` 检测通信链路 FDI。拟议差异是校准通道不读取可被通信攻击污染的邻居报文。原计划还希望在 `S_(ji)(c)=c S0` 的受限工况下，若 `P(1−rho ≤ chat/c ≤ 1+rho)≥1−delta`，给出 `P_FA ≤ P(chi_d² > tau(1−rho))+delta`。

## 冻结模型与边界

**FACT** 数值试验以现有 `simulation/config.json` 的 Baseline-Y5 为底：五节点、二维、400步、A=1.01I、Q=0.02I、P0=I、各节点 H_i=h_iI、R_i=0.05I、五节点双向环、epsilon=0.08。为给接收节点实际链路包，试验用全发送外生日程；没有把 `schedule=None` 的 SoD 当作本轮研究条件。

本筛选不研究水印、历史Replay、缓存恢复、改变Yang增益、攻击者最优性、传感器节点恶意、攻击后补偿或真实闭环事件触发。小试验攻击一条 `0→1` 链路，噪声切换和攻击均在新脚本内生成，不修改冻结配置。

## 既有项目资产及不可重复包装的部分

- **G1**：`reviews/fdi_replay_20261112/g1_decision.md` 已确认完整经验联合 prefix covariance、episode 最大值校准、CUSUM/白化窗口等机制已存在；普通GLS或统计量组合不是新贡献。G1文件保留“固定阈值SoD条件分布另有OPEN”，这不等于本轮的动态工况价值已经成立。
- **G1-R**：`reviews/g1_retroactive_recovery/` 已实现接收端基于本地量测创新和实际接收记录做历史包候选评分/恢复，且最终未知事件测试与失败/误报计数均有报告。本轮“可信本地量测参与链路异常推断”不能被描述成全项目首次使用本地量测；不同之处只可能是把本地信息专门隔离为在线噪声校准通道。
- **G1-R结果边界**：历史包检测、正确归责、估计恢复和真实MSE改善是不同结果；旧报告中的91/100报警、85/100正确归责和clean误报必须按各自Run引用，不转用为本轮噪声工况实验结果。
- **G4**：`reviews/g4_topic_screen/05_research_ranking.md` 没有授权新检测器立项；它要求具体机制、可证明风险性质和强基线增量同时成立。
- **G5及缓存风险审计**：`reviews/g5_direct_competitor_audit/EXECUTIVE_SUMMARY.md` 与 `reviews/distributed_filtering_security_privacy_literature/12_cache_risk_claim_audit.md` 已说明，可信本地量测、残差白化、协方差和卡方等标准组件本身不是创新，且正常噪声协方差不确定时仅靠本地记录不能必然归责攻击来源。
- **先前风险约束恢复**：`reviews/g1r_risk_constrained_recovery/sources/prior_recovery_audit.md` 使用可信本地量测、但目标是历史攻击重构；这不是在线噪声尺度校准，也没有证明新候选已被它解决。
- **先前一般候选止损**：`reviews/final_candidate_feasibility/06_final_go_no_go.md` 对缓存相关性和可信信息不足给出NO-GO。它不直接裁决当前候选，但继承其原则：信息来源受信不代表它足以识别需要校准的协方差模式。

## 本轮验收门槛

1. 公式级竞争审查需能区分既有“攻击数据驱动自适应协方差/NIS”和“CUSUM参数适配”与本候选的可信校准来源。
2. 可信通道必须对主张的噪声变化模式有可辨识信息；否则 `chat/c` 覆盖保证不可用。
3. 公平小试验需要独立无攻击校准/验证轨迹、同一残差、同一episode虚警预算，且报告按单位时间和episode的误报与检测结果。
4. 任一门槛不通过即停止；小样本pilot不用于宣布正式性能或新颖性。
