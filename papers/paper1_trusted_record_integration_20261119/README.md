# 第一篇：可信记录损伤界整合讨论稿 v0.2

**冻结E1标量验证已完成并通过实现/证据验收；本文仍是讨论稿，不是投稿终稿。** 负责人已决定采用理论安全性能分析定位，真实工业B类接口材料不再是继续写作的硬性前提。本文仍主动声明受限信息、信任边界及未验证实际部署。

- [整合阅读稿 PDF](paper.pdf)
- [LaTeX主入口](paper.tex)
- [六章正文与证明附录](sections/)
- [本轮贡献冻结与状态](../../reviews/paper1_integration_and_minimal_experiments/00_scope_and_claims.md)
- [最小充分实验协议](../../reviews/paper1_integration_and_minimal_experiments/01_minimal_experiment_protocol.md)
- [原冻结方案快照，历史DESIGN_ONLY_NOT_RUN状态保留](../../reviews/paper1_integration_and_minimal_experiments/experiment_protocol.json)
- [E1执行报告、原始数据和断言](../../reviews/paper1_e1_scalar_execution/01_execution_report.md)
- [E1审稿前证据验收](../../reviews/paper1_e1_scalar_execution/02_referee_evidence_audit.md)
- [复用旧结果的出处与哈希](../../reviews/paper1_integration_and_minimal_experiments/saved_evidence.json)

章节1–3围绕精确实际预测反馈下的统计证书及双预算损伤阶数；第4章仅在标量中陈述量化反馈和受限审计信息的退化；第5章清楚分开旧二维证据和新增冻结E1标量结果；第6章收束。附录给单拍联合核与一般固定k的统一概率论证。没有增加第三项理论、检测器或新的工程架构创新。

本稿下界证明采用已审核单拍构造；第5章保存结果来自旧两拍构造，保持策略名称，不借用其数值常数充当新构造常数。两种构造分别支持同一阶数的合法下界，不能据此声称数值完全相同。

旧稿 [latex_ecust_20261102](../latex_ecust_20261102/README.md) 保持原样。本文是新目录，不覆盖它的LaTeX、PDF、数据或审查记录。

## 编译与状态

运行 python build.py 仅调用XeLaTeX两遍，生成本文PDF和 [构建记录](build_validation.json)，没有实验入口。需要XeLaTeX、ctex及Windows中文字体。当前环境缺少可选超链接依赖，因此讨论稿PDF按可见DOI文本排版，仓库报告保留可点击来源链接；不为排版修改系统TeX安装。数值方案准备脚本只读旧数据并计算有限协方差常数，不生成状态轨迹。

讨论稿编译检查只验证排版、引用和制品一致性，不替代数学正确性、创新性或投稿验收。当前仍为CONDITIONAL GO。本轮在E1硬性检查和独立汇总检查均通过后才更新第5章。A的实际事件小差异未被本批样本分辨，这项负向证据保留，不能将B路径一致性或A经验零差异冒充总体同律证明。
