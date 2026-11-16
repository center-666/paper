# G1-R / G6 / G7 研究审阅入口

上传日期：2026-11-16（Asia/Shanghai）。仓库：center-666/paper；隔离分支：g1r-e2-status-contract-20261115。

本次根据项目负责人最新指令“有结果上传到 GitHub，方便我和 GPT Web 审阅”，上传此前仅保存在本地的四份审查草稿。上传用于审阅，不表示论文立项、算法验收或新实验授权。

## 建议阅读顺序

1. **最新审查：[G7-R0：SoD 条件残差与阈值](01_core_problem_audit.md)**。建议 NO-GO：SoD 选择效应存在，但原 G1 已使用经验联合矩和周期最大值校准；尚未证明条件化相对正确同分布重标定有实质增量。请重点审核第4—7节的条件分布、首步Gaussian例外和阈值有效性边界，以及第8节文献证据缺口。
2. [G6-R0：历史攻击事后检测方向审查](../g6_retrospective_detection/01_research_direction_audit.md)。继承资产、实际时序、竞争文献及正常通信异常的可辨识边界。
3. [G1-R 28号：B0可辨识性与恢复下界审查](../g1r_risk_constrained_recovery/28_B0_identifiability_and_recovery_bound_audit.md)。数学命题与原创性分开；保留文献及数据缺口。
4. [G1-R 27号：E3后诊断与方向决策草稿](../g1r_risk_constrained_recovery/27_e3_postmortem_and_next_decision_draft.md)。早期候选建议应与后续28号、G6、G7审查结合阅读，不能当作最新立项决定。

正式实验事实以[26号E3报告](../g1r_risk_constrained_recovery/26_e3_formal_experiment_report.md)及其原始结果为准：运行完整性通过，最终研究判据为 NO_GO_PERFORMANCE。上述研究草稿没有更改正式结论。

## 文档状态与证据边界

- 四份草稿按原内容上传，未修改其数学结论、旧结果或历史记录。正文中的“未提交／不推送”描述各原任务结束时的状态；本索引记录随后获得的上传授权。
- G6-R1在后续G7任务收窄前只完成部分分析，没有完整交付报告，本次不将其冒充已完成成果。
- FACT、DERIVED、HYPOTHESIS、OPEN标记按各报告解释。报告的NO-GO是执行助手的审查建议，最终决定由负责人作出。
- 上传前检查四份报告的UTF-8读取、相对文件链接和SHA256；这些交付检查不等于重新证明全部数学或补齐缺失文献。
- Git空白检查提示28号一处行尾空格，以及G6/G7报告末尾空行；为保留原文SHA256，本次不清理这三处格式提示。
- 本次不运行实验，不修改算法、共享仿真、冻结配置或E2/E3数据，不合并main，不操作G2/G5工作区。

## 上传原文 SHA256

| 草稿 | SHA256 |
|---|---|
| G1-R 27号诊断 | `49bb3c81392c5de7a720a86b3437e27a685237b2fc919aff4d328bdaeb2d2096` |
| G1-R 28号B0 | `301351eb91364232b013be444a8729c69af06bd6a56e7ea90d361185b48e5520` |
| G6-R0 | `0cb189abcafccbedf4723df005c5e544837594e48ca5a7ba3a2c80f70656c115` |
| G7-R0 | `bfa37ad4e692aa2d8550f3ae603304b365bfae558953e21f0c106874fe3d2acf` |

本索引与上述四份报告一起提交。Git提交标识由提交完成后的交付消息提供，避免在提交内部形成自引用哈希。
