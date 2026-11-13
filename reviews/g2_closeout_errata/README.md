# G2结项统计勘误

本目录仅只读重析提交 `031d26eaf996b3583b2b2647b54702551466e20a` 的既有v3结果。G2已结项；原始运行、冻结计划和已验收报告保留。本次没有运行新的攻击仿真或下载文献。

- [完整勘误报告](results/2026-11-13_g2_readonly_erratum_r01/g2_erratum_report.md)
- [逐seed重算](results/2026-11-13_g2_readonly_erratum_r01/per_seed_reanalysis.csv)
- [自然预算条件统计](results/2026-11-13_g2_readonly_erratum_r01/natural_conditional_summary.csv)
- [cap与附加保护的配对差](results/2026-11-13_g2_readonly_erratum_r01/paired_cap_decomposition.csv)
- [只读分析源码](code/analyze_errata.py)
- [输入完整性与一致性验收](results/2026-11-13_g2_readonly_erratum_r01/validation.json)
- [G3预注册计划，尚未执行仿真](../g3_partial_observability/g3_preregistered_plan.md)

关键修正：18.75%不是受攻条件检出率；39个无替换seed的恢复为N/A；旧恢复函数的搜索起点还存在强制等待；cap收益须与附加保护收益分开；撤回745798149989作为候选方法间1%改进功效依据的解释。

研究判断不变：合法Replay的真实闭环损伤成立，现有防御尚未被证明存在足以立题的新缺口。不重启G1-R的GLS/influence-capsule开发。

复现（仓库根目录，使用全新Run ID）：

```powershell
.venv/Scripts/python.exe reviews/g2_closeout_errata/code/analyze_errata.py --run-id 2026-11-13_g2_readonly_erratum_reproduce
```

同名结果目录已存在时程序停止，禁止覆盖。均值CI以seed为单位，受攻条件样本仅9个；描述性区间及最终报警均不能当作因果检测保证。

已另行只读复核攻击/状态索引、条件分母、恢复搜索起点及配对CI，关键数值一致。报告中“首警”指首次替换之后首次观察到报警/低权重状态；该状态可能是缓存期间持续拒绝，不能理解为一个新的独立报警触发。
