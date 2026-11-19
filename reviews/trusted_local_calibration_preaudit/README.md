# 可信本地参照在线校准：立项预审

2026-11-19；基线 `9901785cf565e3bcfbe814080b04b997fd661377`。**当前决定：NO-GO，停止本候选开发，等待研究负责人审核。** 这是立项证据不足的决定，不是不存在任何有效方案的数学定理。

- [最终决定](04_final_decision.md)：全文排重、模型边界、探索性结果与停止条件。
- [范围与旧资产](00_scope_and_project_assets.md)：不混用原G1检测/恢复或水印研究成果。
- [三篇全文公式审查](01_competitor_formula_audit.md)：RACKF、DCI、Adaptive Parameterisation均已取得全文；包含原文页码、公式和保证的边界。
- [模型反例与条件虚警界](02_identifiability_counterexample.md)：本地可信不等于对所有噪声变化可辨识；给出Baseline-Y5矩阵反例。
- [修正后的pilot结果](03_small_pilot_results.md)：同一真实本地参考残差、正确12维联合协方差、独立校准/验证/测试。
- [机器结果](results/pilot_summary.json)、[逐seed证据](results/per_seed_scores.csv)、[确定性复算](results/analytic_checks.json)。
- [来源哈希](sources/source_manifest.json)、[完整性记录](sources/integrity.json)。PDF留本地，不上传论文全文。

## 复核

需Python和NumPy。在仓库根目录：

```text
python reviews/trusted_local_calibration_preaudit/verify_analytic.py
python reviews/trusted_local_calibration_preaudit/run_small_experiment.py
```

第二条会按脚本中固定种子重新生成本轮小试验并写本目录results，不是仅只读检查；本次已执行，审阅报告无需重跑。没有调用旧E2/E3或改写旧Run。

## 必须保留的更正

`invalidated_v0/` 中的第一版用了错误的参考残差，不是本候选的性能证据。其代码、输出和当时草稿都保留并标为无效；不要从其中选取有利数字。当前报告只用v1，不增加攻击强度或改变窗口来补救性能。

本试验没有忠实复现三篇完整算法或稳健尺度基准，因此不宣称已击败或已被它们击败。共同校准预算也不等于实际FAR完全相同。当前没有满足用户要求的清晰增量，按停止规则归档。
