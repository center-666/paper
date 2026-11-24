# TRSR Oracle 恢复可行性试验

本阶段按 S11 提议先检验恢复机制本身。实验给恢复器 oracle 攻击起止和幅值，只比较选择性历史重处理、恢复权重和精确攻击补偿。它不验证攻击历史审计、confidence set 或实际部署检测率。

- [冻结试验协议](protocol.json)
- [确定性代数检查与 Oracle pilot](run_oracle.py)
- [运行结果](oracle_results.json)

恢复支路在 oracle 攻击窗口内忽略整个 send observation/event 输入，silent 仍使用可信中心伪观测。窗口外处理实际载荷。忽略窗口内 send bit 是一种恢复估计规则，不声称它是完整记录下的条件后验。Oracle candidate branch 用真实攻击幅值纠正 send payload，作为模型条件均值参照。所有支路共享同一 monitor 驱动的 center/event 记录。

恢复权重使用已知候选的条件均值污染方向。该设置是 oracle 上界，部署版必须把真实候选替换为可信历史集或外包，并单独证明风险条件。

200 episodes/cell 是诊断 pilot，不是确认性性能实验。随机种子已冻结，结论不得用于投稿的显著性主张。
