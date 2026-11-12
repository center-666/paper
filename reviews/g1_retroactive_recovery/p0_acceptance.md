# P0最终验收

2026-11-13。唯一最终入口：[acceptance.json](results/g1r_p0_verified_20261113_v1/acceptance.json)。
此前p0_final_audit_02–05漏检响应矩阵方向，完整PASS已撤回。

| 项目 | 结论 | 验证 |
|---|---|---|
| 全时域节点/缓存递推 | PASS | 76800状态分量行、153600缓存分量行，全部≤1e-10 |
| 单位响应矩阵 | PASS | 2个独立方向完整仿真对照，最大<1.89e-13 |
| 合法接收信息 | PASS | 特征函数只有local_y/own/received_aligned/H |
| 时钟/保持/预测 | PASS | 全48seed、clean/FDI/Replay逐时检查 |
| 因果性 | PASS | 未来值置NaN不影响前缀 |
| 原Yang等价 | PASS | logger返回1，与vanilla正常轨迹相同 |
| 新CSV格式 | PASS | 实际CSV写出；旧JSON伪CSV另存格式副本 |
| 公平性能 | LIMITED | oracle定位、FPR未匹配、旧seed复用、影子输出 |
| SoD闭环/全网回写 | NOT TESTED | 未扩展宣称 |

配置、源哈希、拟合表及逐分量数据见最终Run，人工审计见07/08。
保护文件及所有旧Run逐个哈希校验未变。P0通过不是方法新颖性或Deghat复现通过。
