# 阶段十数值合同执行记录

理论基线 `d92c39cb1152f335d5b347ca9a2cc8f11924a64e`，验收方案 `803a0399c438552d3a5f9f71f88aab49792278e4`。

本轮从N01推进实数nominal monitor、binary64 monitor和实际输入的定义，建立误差到候选似然、有效动作风险的连接。

- [定义、推导与源码对应](01_numerical_contract.md)
- [数值审计原型](numerical_record.py)
- [确定性核对及结果](numerical_contract_checks.json)
- [统计口径](statistical_conventions.json)
- [验收执行状态](execution_status.md)

运行 `python reviews/paper2_stage10_numerical_contract_20261123/check_numerical_contract.py` 可复算确定性检查。需要NumPy和SciPy。原型接受声明为精确值的观测和实际monitor的binary64状态，复用已有外向区间与似然缓存。有限十进制输入的算术合同已有实现，连续真实输入转换区间、完整证书签发集成与24条历史轨迹的全流程再认证仍需后续验收。

本次修复在似然记录提交前按实际预测坐标检查量化中心，并增加边界、越界回滚和合法重试检查。[区间观测原型](interval_observation.py)单独处理中心合法性的三值判断与发送选择项的点态区间外包，尚未接入似然缓存或证书。`check_monitor_horizon.py` 可对指定确定性事件序列进行有理数参考的逐拍误差检查。

[舍入观测研究](02_rounded_observations.md) 给出单拍质量公式、区间质量原型、阶段九执行路径与多拍非高斯滤波的限制。复算入口为 `check_rounded_mass.py` 和 `trace_stage9_monitor.py`。
