# Task 1.6：确定性验证报告

## 范围

`code/task1_formula_checks.py`只读取Task 0.5已保存的JSON/CSV/一致性报告，并运行纯代数fixture；不导入simulation.engine/model，不调用随机数、simulate或generate_data。

## 结果

| 检查 | 结果 |
|---|---|
| Task 0.5计数独立核对 | PASS；增加11、减少14、不变7 |
| 首次节点1事件分叉 | PASS；32/32 |
| 首次分叉时延 | PASS；1–55拍，中位数2 |
| 首次状态污染公式 | PASS；最大误差1.7208456882e−15 |
| 首次裕度公式 | PASS；最大误差1.2767564783e−15 |
| 共同发送模式下块矩阵与逐节点更新 | PASS；32种模式组合，与直接双轨迹相减一致 |
| 固定模式矩阵组合 | PASS；结合律误差在浮点容差内 |
| raw/aligned缓存、参考值及两种时钟四分支重置 | PASS |
| 不分叉充分条件人工fixture | PASS |
| timeout掩盖人工fixture | PASS |
| 模式分叉不强制非零值差人工fixture | PASS；状态快照，不声称从共同初态可达 |
| Yang一致性融合下缓存重置的估计污染递推 | PASS；逐点双臂公式相减 |
| 同一污染方向下真实平方损失可降/可升 | PASS；代数例子，不是MSE试验 |
| raw相同、年龄不同而对齐值不同 | PASS |
| 差分状态缺少健康基准时不闭合 | PASS；快照反例，不声称轨迹可达 |
| 失败推导反例 | PASS |
| 分析脚本AST无仿真/RNG调用 | PASS |
| 三个输出的字节级复算 | PASS；`--verify` |

共12组检查验证代数、来源和历史结果一致性，不是新实验，也不是全模型概率证明。Task 0.5每Seed有多次Replay；首次局部公式不能外推为单次Replay全时域性能。完整脚本、环境和输出哈希见本目录的`SHA256SUMS.txt`；逐Seed复核表及32个保存数据首次注入核验分别见`validation/seed_reaudit.csv`和`validation/first_replay_recheck.csv`。
