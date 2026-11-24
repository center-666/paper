# S11 冻结交付

本目录记录“有限持续时间 FDI 攻击结束后的可信审计与估计恢复”研究任务书。当前只冻结研究合同，没有开始实现新算法、随机 pilot 或 confirmation 实验。

- [S11 任务书](S11_task_charter.md) 固化 V2 与稳定压力模型、中心/event 时序、8/12-bit 上行量化、攻击权限、三项待验收命题、恢复接口、对照和停止门。
- [机器可读协议](s11_protocol.json) 供后续实现和实验脚本读取。
- [来源清单](source_manifest.json) 绑定任务书、协议、继承模型/证明/代码和旧恢复失败证据的 SHA-256。
- [合同验证器](validate_charter.py) 重验矩阵可观测性、onset prior 质量、场景数量和来源哈希。

本文件中的量化范围、stable stress 矩阵、攻击幅度范围、reference 模板和确认样本规则是本轮明确选定的研究假设。它们不是已有论文定理或实验结果。有限 code cells、饱和尾概率、finite-duration likelihood、置信覆盖、replay conditional risk、MSE 收益和近邻全文查新均未完成。旧 Stage9 连续载荷与 binary64 实验只作为先前证据，不能当作本任务的 finite-bit 验证。
