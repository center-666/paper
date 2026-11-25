# WP2 离线安全圆盘校正验收报告

## 几何实现

`code/corrector.py` 实现了以下步骤。

1. 对每个存活起点的幅值区间端点构造污染向量端点。
2. 在 \(W^{1/2}\) 坐标中检查幅值区间是否跨过零点。
3. 用小规模单纯形枚举求凸包最小范数锚点。
4. 在安全圆盘约束上进行候选投影，并沿锚点到候选点的线段回拉。
5. 对所有端点重新计算最小风险改善，数值不足时回退为锚点或零动作。

`code/check_wp2.py` 对双端点正区间、跨零区间和原点分离区间进行了精确输入下的确定性夹具。三项检查均通过，返回动作对所有端点满足安全约束，数值余量为 `1e-9` 以内。

## 严格 No-Go

本工作包原计划还要求直接读取冻结确认集主工况的 56 条中间记录，比较原 M3 与 M3-Opt 的条件改善和实际累计降损。当前冻结目录中的逐轨迹 JSON 只包含

- 512 拍汇总损失和条件改善；
- 四个查询时刻的方向、门限、成功状态和证书日志；
- M2/M3 的下界快照和计时；
- 轨迹级来源哈希。

它不包含逐拍事件、中心、载荷、Monitor 状态、污染响应序列、M3 实际动作序列或每个端点的历史区间。因此这些文件不能支持 M3-Opt 的零重跑回放。重新生成这些中间记录会改变“零重跑离线验证”的任务性质，也不能把最终汇总反推成逐拍证据。

因此 WP2 的裁决为

```json
{
  "geometry_gate": "PASS",
  "offline_ablation_gate": "NO-GO",
  "proceed_to_wp3": false,
  "reason": "Frozen Stage 7 confirmation artifacts lack the public per-step record and action trace required for a zero-rerun M3 versus M3-Opt comparison.",
  "required_artifact": "A future confirmation run must archive the shared public prefix, per-step monitor/action records, and endpoint interval snapshots before M3-Opt can be compared."
}
```

## 结论边界

几何程序可以作为后续方法开发的独立组件。当前结果不能支持 M3-Opt 的实际降损提升、条件改善提升、覆盖保持或计算收益主张。WP3 的残差唤醒和 float64 热路径优化暂不启动，避免在缺少可回放基线的情况下继续扩大实验范围。
