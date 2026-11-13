# G5定向竞争审计

**状态：部分完成。** Ye正式全文与Wang作者稿已审；Gao公式级审计仍缺全文。当前没有可立项的新机制；最多保留F一张条件问题卡，不启动算法。

- [研究负责人执行摘要](EXECUTIVE_SUMMARY.md)
- [01 Gao全文与审计前置状态](01_gao2026_formula_audit.md)
- [02 Ye/Wang原式审计](02_ye_wang_privacy_attack_audit.md)
- [03 A与F决定](03_A_vs_F_decision.md)
- [04 唯一条件问题](04_one_problem_proposal.md)
- [下载清单](sources/download_requests.md)
- [下载日志](sources/download_log.json)
- [独立代数核验](results/2026-11-13_g5_formula_checks_r01/checks.json)

PDF、全文提取和原页截图留本地，不加入公开仓库；来源与哈希支持核验/自行下载。未更改G1至G4结果、共享仿真代码及冻结计划。

从仓库根运行 .venv/Scripts/python.exe reviews/g5_direct_competitor_audit/code/formula_checks.py --run-id 新ID 可复核代数。现有Run禁止覆盖；这些不是新防御或随机模拟。
