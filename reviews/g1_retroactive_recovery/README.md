# G1-R 最终审计交付（2026-11-13）

**研究决定：历史污染现象和固定模式传播模型获得支持；维持终止 post-cache GLS / influence-capsule 作为独立创新。** 本轮没有完成公平的 Deghat 离散性能复现，也没有找到值得重新立项的新机制。G2 保持独立。

## 给研究负责人的执行摘要

- **成立的结论。** 在既有五节点模型、固定外生发送日程、单次真实历史包 Replay 下，恶意包于 q=208 退出缓存后，后续未经再次篡改的发送仍携带间接污染。48 个配对 seed 的全时域独立递推与完整仿真一致，最大分量误差约 2.31e-13，小于固定回归容差 1e-10。此结论没有推广到闭环 Send-on-Delta。
- **恢复收益。** 指定 Replay 场景的接收节点恢复窗 MSE 超额为 0.816381；已知事件位置下，标准 GLS 可以明显降低影子输出误差。这里的修正未写回全网节点和缓存，因此不是已部署的全网恢复协议。单次 FDI 的同期损失很小。
- **审计纠错。** 原 Run 04 仅核验缓存替换前；旧分歧特征读取了未发送的邻居内部估计。本轮中间版本还发现响应矩阵左右乘错误，相关 MSE 和过早的 P0 PASS 已撤回。原数据、失败记录和格式错误原件全部保留，正确格式副本另存。
- **方法增量。** 合法缓存分歧与仅本地 innovation 的同窗口 MSE 配对区间跨零，正常误修正风险也未匹配。当前收益可由标准传播和 GLS 解释，不能据此宣称新算法或新定理。
- **强基线边界。** Deghat 2019 已有动态攻击/误差跟踪和校正输出；其式(18)需要额外邻居误差估计通信，连续 LMI 与当前离散缓存模型不直接等价。完成了原式映射和离散误差方程核验，未完成新的离散设计，故停止性能宣称。没有把未完成适配说成对方方法无效。
- **下一步建议。** 结束当前候选开发，保留后续可信量测验证历史数据的基础机制。只有出现未知事件、有限存储或实际通信约束下可复现的标准方法缺陷，并形成相应新机制与理论证据，才重新评审。当前不增加模块、不写论文、不扩展仿真。

## 审阅顺序与证据

| 文件 | 内容 |
|---|---|
| [07 全时域传播验收](07_full_horizon_propagation_audit.md) | 节点、缓存、age=0、后续发送间接污染 |
| [08 信息权限审计](08_information_permission_audit.md) | 合法特征、同窗口比较、误修正及资源口径 |
| [P0 独立验收表](p0_acceptance.md) | 通过、撤回与未覆盖项 |
| [09 Deghat 逐式映射](09_deghat_discrete_baseline.md) | 原文页码/公式/定理、离散映射及适配障碍 |
| [10 最终研究决定](10_final_research_decision.md) | 攻击有效性、新颖性和论文可行性分别判断 |
| [结果状态及哈希索引](run_status_index.json) | 完整 Run ID、失败/撤回状态、各文件哈希 |
| [最终数据校验](final_delivery_validation.json) | 结果结构、源哈希、G2保护、基准 engine 对照 |

最终有效数值入口为 [P0 Run](results/g1r_p0_verified_20261113_v1) 和 [P1 结构 Run](results/g1r_p1_structure_20261113_v1)。中间 Run 仅用于追溯，不能把目录内历史 PASS 字段当作当前认可。不同 Run 复用了相同 seed，不构成增加样本量。

## 复现

仓库根目录运行，依赖 Python、NumPy、SciPy；具体版本见状态索引。所有重跑必须使用不存在的新目录，避免覆盖旧实验。

```powershell
.venv/Scripts/python.exe reviews/g1_retroactive_recovery/code/validate_final_delivery.py
.venv/Scripts/python.exe reviews/g1_retroactive_recovery/code/reproduce_audit.py --phase p0 --out reviews/g1_retroactive_recovery/results/g1r_p0_reproduction_NEW_ID
.venv/Scripts/python.exe reviews/g1_retroactive_recovery/code/reproduce_audit.py --phase p1 --out reviews/g1_retroactive_recovery/results/g1r_p1_reproduction_NEW_ID
```

复现入口保留科学程序原文，只把 P1 的固定输出目录改为命令行目录，并跳过新克隆中不存在的 G2 私有工作文件哈希检查；实际存在的保护文件仍核验。该路径变换和入口哈希写入新 Run。P1 入口只重跑误差/输出方程检查，不是 Deghat 检测器。

原始 Run 在含未提交 G2 扩展的 engine 上执行，该文件未修改也未提交。独立校验用基准提交 db7dabd 的公开 engine 对同一个既有 seed 的 clean/FDI/Replay 路径作对照，状态和 Replay 来源完全一致；这是一项明确范围的兼容检查，不是所有 engine 分支等价证明。复现记录保留实际使用的源码哈希，不冒充原 Run 哈希。

源码/结果文件保留原始 SHA-256 字节哈希，新归档结果禁用 Git 换行转换。索引另外记录仅将 CRLF 转为 LF 的哈希，以核验旧版本文本的检出差异；这不允许任何数值或算法内容变化。最终拟合数组一并归档；旧结果原件不改，JSON 误用 CSV 后缀的迁移见 [格式修复索引](results/g1r_format_repair_20261113_v1/index.json)。下载论文原文仍在本地文献库，来源见 [文献索引](sources/README.md)；本轮没有新增下载。
