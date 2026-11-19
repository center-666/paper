# Paper 1：部分观测与可信事件窗口独立审查

本目录审查一个候选深化方向：在 \(y=Cx+v\) 的部分观测模型下，用目标时刻后的连续 \(L\) 次静默事件限制攻击损伤，并进一步比较攻击可达方向与事件不可感知方向。

## 文件索引

- 00_scope_and_source_status.md：模型、量词、来源状态和本轮边界。
- 01_hu2025_fulltext_extraction.md：Hu 等 2025 全文提取与公式级排重。
- 02_joint_silent_window_derivation.md：联合 Gaussian 事件概率和条件 TV—MSE 上界所需条件。
- 03_attack_reachable_observability.md：攻击可达空间、反例、窗口概率限制和 OPEN 项。
- 04_counterexamples_and_stop_gate.md：最终裁决和停止门。

## 最终裁决

OPEN（研究可行，但尚未形成可投稿的新定理）。

Hu 2025 是 FULLTEXT 的健康多传感器事件估计论文，部分覆盖观测分解和集体可检测性，但不覆盖攻击安全问题。Liu 2024 仍是 OPEN，因全文未取得不作定理级排重结论。联合静默公式在给定模型下可推导；普通观测矩阵满秩只是标准工具。潜在的新内容必须同时证明攻击可达性、合法因果构造和受限记录的统计隐蔽性。

本轮没有修改原稿、没有运行新实验、没有启动三预算或多维量化研究。
