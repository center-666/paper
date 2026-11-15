# G1-R Task E2：正式执行计划（等待负责人授权）

日期：2026-11-15。此文件是执行计划和预启动审计记录，**不是正式实验授权**。当前没有有效授权文件；本计划阶段没有生成正式Seed轨迹。

## 当前状态

隔离分支 `g1r-e2-status-contract-20261115` 已推送。C0提交 `12cd6517567e655a1a933aae424ba2641d564e86` 的远程分支SHA与本地SHA一致。当前分支包含C0运行器和后续只读/统计审计加强，工作区干净。没有创建 `g1r_e2_run_*` 目录，没有E2/E3结果。

冻结研究条件保持不变：Yang 2014型五节点估计器、固定外生gap-8发送日程、单次历史Replay、Hard/Soft/Set三种恢复方法、12维创新、决策216/目标217、U=0.051261及冻结门限。共享 `simulation/engine.py`、`simulation/model.py`、估计器、协议、校准门限均未改。

## 只读绑定清单

以下值由隔离分支当前代码的 `--show-authorization-bindings` 产生。其输出为 `authorized=false`，不产生授权或数据。

| 绑定项 | SHA256 |
|---|---|
| 当前隔离分支 HEAD | `12cd6517567e655a1a933aae424ba2641d564e86` |
| 运行器最终代码 | `b8a0b0e7905fd6d99e491d689ea9add53454130d04eacb02185a749a61d2ccec` |
| v2协议 | `7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab` |
| 冻结校准门限 | `3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00` |
| 正常+攻击Seed清单绑定 | `8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946` |
| 冻结实验配置 | `34f9404f6f53fe9c40d630bacc194e15d268de4cbe921cf1430c297a783f33c2` |
| Task 5校准manifest | `7ccd2a04d94e464a4f4b2b0ef67c134bbd3c613d73f08b95e1b0aa91663ee813` |
| Replay联合矩阵 | `c02f7d0041fa568246d2788084fe2c78b9a5f912ab03166a0bb7830f3efa7c0a` |
| E2历史Seed扫描报告 | `e65c9a62de9e21395a029e0af8b54cdc9dbfb146f95aa5e15dffcba7e43a919c` |

阈值数值交叉检查：Hard `7.130518504393956`，Soft `0.20737147161542802`，Set `0.0`；U `0.051261`。这些值未重新校准。

## Seed与数据设计

正常Seed固定为 `141420000–141420199`，攻击Seed固定为 `141430000–141430199`。每组200个，合计400个。只读审计文件列出全部400个Seed，记录 `collision_count=0`；检查范围包含可读工作区文件、数组和归档，外部磁盘/备份不在范围内。

正常场景每Seed一条轨迹。攻击场景每Seed共享一份数据及健康配对轨迹，随后使用8个冻结事件、年龄32/64/96生成24个相关场景。每个场景运行3种方法。主推断单位仍为Seed；同Seed内事件、年龄、时间点不得计作独立样本。主场景为edge 0、Replay时刻200、age64、检测窗口211–216、目标217。

## 授权检查表

| 项目 | 检查结果 |
|---|---|
| 远程分支与本地SHA一致 | 通过，均为 `12cd6517567e655a1a933aae424ba2641d564e86` |
| G5未提交修改保持在主工作区 | 通过；本轮未触碰、未提交 |
| 400个Seed与冻结协议清单一致 | 通过 |
| 历史扫描结果 | 扫描范围内无冲突；外部备份未扫描 |
| 估计器/校准器/协议/门限/模型输入哈希 | 通过；B.1与R12运行记录可逐项复核 |
| Runner、Python、NumPy、SciPy及BLAS记录 | C0快照通过；运行环境与R12记录一致 |
| Runner确定性测试 | 32项通过，含虚构Seed的20批独立统计CSV复算 |
| B.1状态适配器与原Proposal等价 | 5项适配器测试通过；30组已缓存Proposal等价记录保留 |
| E2授权文件 | **未提供；仓库模板为 `authorized=false`，不得用于运行** |
| 正式执行 | **未启动；本计划不构成启动授权** |
| E3授权 | E2之外的独立授权，当前未提供 |

授权缺失时的拒绝行为已验证：`--formal-e2`退出码2，且不创建Run目录。运行器默认dry-run只使用既有Task 5 Debug缓存和seed 0确定性fixture。

## 正式启动命令

负责人复核绑定表并提供有效的外部授权文件后，才可执行：

```powershell
$py = 'C:\Users\zhongxin\shixidoc\mypaper\.venv\Scripts\python.exe'
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli `
  --formal-e2 `
  --authorization '<负责人提供的E2授权JSON绝对路径>' `
  --out 'reviews/g1r_risk_constrained_recovery/results/g1r_e2_run_<负责人批准的唯一RunID>'
```

授权文件必须显式包含 `scope="E2"`、`authorized=true`、非空负责人和授权编号，并且 `bindings` 五项与本表完全相等。运行器还会把授权文件SHA、负责人、配置摘要写入Run配置；中断恢复要求这些字段与现存Run一致。配置、代码或绑定任何变化都会导致授权失效。

正式运行资源估算来自R12 dry-run：约116秒，规划范围约1–4分钟；结果文件粗估约36.7 MB（不含失败归档开销）。时间估算使用缓存proposal实测和历史Debug运行残差，不是运行保证。E2结果只评价集合覆盖、非零动作率和正常误动作率；E2通过也不会自动启动E3。

## 等待决定

**当前唯一下一步：等待研究负责人复核上述SHA并提供/签发绑定一致的正式E2授权。** 在此之前不得运行正式命令、不得生成正式Seed轨迹、不得重新校准或更改算法/门槛。负责人未批准时，保持现状并停止。
