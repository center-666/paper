# P5.4审阅入口与复核范围

主报告：[P5.4_final_novelty_audit.md](../P5.4_final_novelty_audit.md)。

- [来源版本核对](01_version_reconciliation.md)：2013 v1、作者机构修订、IEEE期刊VOR分别记账；Dolk、Lu、Sun正文定位。
- [来源清单](02_source_manifest.md)：论文链接、审读版本、页码与SHA256；标明继承旧审查和本轮重新核阅。
- [主张—证据矩阵](03_claim_matrix.md)：T1/T2/T3、P5.2/P5.3与实际性能各自可以支持的结论。
- [完整性清单](04_integrity_manifest.json)：主报告及本包文件SHA256，不对清单自身作循环哈希。

在仓库根目录执行：

```powershell
python -B reviews/ack_budget_v1_theory/p54_novelty_reconciliation/verify_integrity.py
```

该程序只读取本报告包并核对哈希，不导入估计器、理论枚举器或仿真器，不访问外部PDF，不生成轨迹，不写任何验证数据。清单描述的历史研究结论仍须查看所引用证明和原始数据；文件哈希通过不表示数学新颖性已经通过。

旧10—13号审查和P5.2/P5.3保留，未被本轮改写。所有文件均是基于P5.3最终提交66b86768新增；无论文主稿、代码算法、配置或旧结果改动。历史P6停止点通过固定提交链接归档，未合并到本分支。P6-LT未启动。
