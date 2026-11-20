# 量化反馈隐蔽污染的有限多拍可持续性

**结论：污染可以长期维持，但不必发散。** 本轮完成解析证明与自查；一般参数下的匹配界和独立新颖性仍为OPEN。正式论文、旧理论及原始数据均未修改，没有新增仿真或优化。

基准提交6b429cabd740da2da7516256c8aa2c52e070984b。用户已授权提交推送，本目录单独交付。

## 可引用结果

1. 同物理耦合下若整段事件/量化码一致，则每拍后验差有格宽硬限；健康条件均值正交性给J_t=E e_t²。记录需包含最后一个损伤时刻的下一码。
2. 当Q>0，协方差归一化误差递推给时间一致的条件偏差半径。对整个前缀TV预算，平均真实损伤有C_delta delta²+C_epsilon epsilon上界，常数与时域T无关；保留协方差分布变化项。此界不要求路径相同。
3. 有理数三拍反例证明：偏差收缩不保证未来码字一致。包括S1原参数下的明确正概率反例，不靠浮点端点或模拟。
4. 在明确的A=1,Q>0子模型，合法发送后“修复历史残差—中央半格重新注入”策略对每个有限T保持整段事件/码字逐路径一致，并保持正的期望平均损伤。固定b、小delta下，上下界为对T统一的Theta(delta²)。这个特例未外推到S1/U1。

## 文件

- [00_scope.md](00_scope.md)：范围和记录索引。
- [01_recursion_and_horizon_bounds.md](01_recursion_and_horizon_bounds.md)：递推、MSE分解、Q>0的时间一致全历史TV界。
- [02_silence_viability_and_sustained_witness.md](02_silence_viability_and_sustained_witness.md)：有限静默可行区间、两个三拍反例、A=1持续构造。
- [03_parameter_regions_and_decision.md](03_parameter_regions_and_decision.md)：S1/U1长期系数上界、参数依赖和停止决定。
- [04_literature_comparison.md](04_literature_comparison.md)、[literature_sources.json](literature_sources.json)：TAC近邻全文定位，TSIPN近邻全文缺口。
- [check_algebra.py](check_algebra.py)、[algebra_validation.json](algebra_validation.json)：43项确定性检查，包括Fraction精确三拍不等式；不是形式化定理认证。
- [verify_delivery.py](verify_delivery.py)、[delivery_validation.json](delivery_validation.json)：受保护文件哈希、文档和交付范围。
- withdrawn开头的两份txt保留已明确撤回的错误草案，不是研究结果，不得引用。

## 验收边界

本轮没有独立外部审稿或形式化认证：完整论证由同一研究助手复核，代数脚本只检查特定恒等式和常数。前期进度文字曾过早声称S1永久构造，已在正式报告中撤回。正确结果仅是S1有限分叉反例与Q>0上界，持续下界只证明A=1特例。

过程噪声Q=0、一般A的持续下界、非零TV紧性、防御参数最优选择、实际工程损害与有限比特实现仍未解决。当前不重构现有论文、不自动开启实验。
