# 主动链路注入诱导的SoD时序泄漏：G0/G1审查

范围：只核实原SoD代码、三篇指定直接近邻，及附件中的标量互信息命题。未运行五节点试验、未生成随机轨迹、未改引擎/模型/配置。

- [SoD代码与范围](00_scope_and_code_audit.md)
- [G1标量信息泄漏证明](01_scalar_information_leakage.md)
- [G0公式级竞争审查](02_fulltext_competitor_audit.md)
- [阶段裁决](03_stage_decision.md)
- [标量确定性复算脚本](verify_scalar.py)
- [复算数据](results/g1_scalar.json)
- [文献版本与SHA256](sources/source_manifest.json)

当前判断：G1在附件限定的单事件高斯符号例子中通过；G0没有找到三篇文献与“入站估计注入因果地改变下一SoD事件”的完全等价式，但这不构成新颖性证明。G2五节点最小试验没有在本阶段运行，需要后续独立审核/授权。
