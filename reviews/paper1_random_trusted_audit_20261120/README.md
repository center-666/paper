# 量化反馈下随机可信审计：最小研究

**最终判断：调整。** 总体分布结论成立，冻结实验实现通过，但预设条件残差检测器对当前小幅攻击的实测报警率接近1%误报背景；低频审计尚未显示等安全收益下的总成本优势。未改论文，未扩展多维、有限比特或任意多拍攻击。

研究基准：19e7b7d8。实验源与配置冻结提交：**1e384e98**。只有一次预设运行；所有旧源码和数据原样保留。

## 入口

- [固定攻防协议](00_protocol.md)、[机器配置](protocol.json)
- [TV混合关系与条件残差推导](01_theory.md)
- [执行与证据验收](02_execution_and_evidence.md)
- [五项工程问题与最终裁决](03_engineering_decision.md)
- [完整报警率/区间表](presentation/all_detection_tables.md)、[损伤/成本/样本量表](presentation/damage_cost_sample_size.md)、[可视化](presentation/detection_rates.svg)

## 主要结果

审计位H独立、动作提交后抽取、被记录且不改变触发更新时：
\[
\Delta_\rho=(1-\rho)\Delta_C+\rho\Delta_D.
\]
对目标单次攻击、下一拍无攻击的策略类，rho>0与零TV可推出动作零。对反射见证Delta_C=0，故Delta_rho=rho Delta_D。它不是有限样本高检出率结论。

最大精度、10%审计时：S1/U1可用前后发送审计样本仅占1.011%/1.132%；条件健康FPR为0.905%/1.213%，符号攻击报警率0.943%/1.011%，反射报警率1.132%/0.843%。这些FPR是测试结果，未根据它们重新调阈值；不能宣称每个固定门限都已保证真实FPR不超过1%。

同一设置下，达到80%批量功效的正态近似规划值为：反射约220万/64万独立episode，符号约3509万/1023万。它不是一次孤立攻击的后续连续窗口，也不是已实测功效。降低rho主要延长等待，规划总认证包数基本不下降。

## 原始制品与复现

- [freeze.json](freeze.json)：任何随机输入前的源哈希、环境与参数哈希；其中“未开始”标志是冻结时状态，不作事后更新。
- [input_manifest.json](input_manifest.json)及inputs/：每模型健康校准131072和独立测试262144条基础episode，四份合成NPZ及哈希。
- [experiment.py](experiment.py)：源冻结后未修改；复用旧E1的量化/符号门控，首次实现经证明的密度平衡反射。
- [audit_results.py](audit_results.py)：不导入运行器的原始数组复算，697项检查全部通过。
- [run_preflight.json](results/run_20261120_v1/run_preflight.json)、[run_completion.json](results/run_20261120_v1/run_completion.json)、[result_manifest.json](results/run_20261120_v1/result_manifest.json)、[独立数组审计](results/run_20261120_v1/independent_array_audit.json)。
- results/run_20261120_v1/raw/：每模型/精度/策略的原始事件、动作、得分、MSE、更新状态；数组行就是基础episode编号，相关方案逐行对齐。
- results/run_20261120_v1/calibration/：实际健康校准得分和事件；thresholds JSON保存阈值。
- [完整单样本汇总CSV](results/run_20261120_v1/single_test_results.csv)、[窗口CSV](results/run_20261120_v1/window_results.csv)、[全量认证CSV](results/run_20261120_v1/full_auth_results.csv)、[解析矩及样本量JSON](results/run_20261120_v1/quadrature_and_sample_planning.json)。
- [summarize_results.py](summarize_results.py)：运行后新增的只读排表/绘图脚本，不生成随机样本。
- [preflight_initial_endpoint_failure.json](preflight_initial_endpoint_failure.json)保留非二进制浮点端点预检失败；[preflight.json](preflight.json)解释其处理。正式模拟未删样本、未放宽码字相等断言。

使用Python 3.11.18、NumPy 2.4.6；来源冻结记录保存环境。已有制品可直接运行audit_results.py及verify_delivery.py进行核查。experiment.py依次提供freeze/generate/run阶段，故意拒绝覆盖已存在输入或结果；若复现随机生成，应在保留本交付的独立副本中采用相同源与配置，不能在本目录覆盖已交付证据。

## 限制

本轮目标k=0，三档精度和物理模型继承E1但不是E1原k=4实验；检测器没有攻击标签/真实状态输入。全量认证基准假设真实载荷受到理想保护并正常送达，和“rho=1只审计下一拍”不同。未测密码实现、真实字节编码、能耗、时延或应用风险货币价值。此前未完成的大修候选没有被修改或并入提交。本研究只关闭本轮最小任务，不自动启动新的审计机制。
