# G1-R E2 正式授权审批申请

日期：2026-11-16  
状态：**待负责人签发；不是有效授权；未启动正式实验**

本材料仅提交 E2 审批所需的可复核信息。代码审计基线（提交本申请材料前）为
`49d096c1739232650351fbd3360332a722c6d35d`，隔离分支为
`g1r-e2-status-contract-20261115`。本申请材料的提交只新增审批记录，不改变冻结代码、协议、门槛或 Seed 清单；主工作区的 G5 未提交改动不在本分支内。

## 审批依据

| 项目 | 证据 |
|---|---|
| P0 审计 | [`19_e2_prelaunch_integrity_audit.md`](19_e2_prelaunch_integrity_audit.md) |
| 71 项确定性测试 | [`tests.json`](results/g1r_e2_prelaunch_integrity_20261116_r06/tests.json)、[`tests.log`](results/g1r_e2_prelaunch_integrity_20261116_r06/tests.log) |
| 环境实时比对 | [`live_environment.json`](results/g1r_e2_prelaunch_integrity_20261116_r06/live_environment.json) |
| 缓存 Proposal 等价性 | [`proposal_equivalence.json`](results/g1r_e2_prelaunch_integrity_20261116_r06/proposal_equivalence.json) |
| R06 文件与哈希清单 | [`manifest.json`](results/g1r_e2_prelaunch_integrity_20261116_r06/manifest.json) |
| 旧绑定失效及新绑定来源 | [`final_assets.json`](sources/e2_prelaunch_integrity_20261116/final_assets.json) |

R06 的机器可读结果为 `tests_run=71`、`pass=true`、`failures=0`、`errors=0`、
`formal_seed_generation_calls=0`、`E2=false`、`E3=false`，并记录冻结源文件未改变。
环境核验显示 Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1 及规范化 BLAS 指纹与校准基准一致。
30 组已缓存 Proposal 逐项 `score_exact=true`、Proposal/action 最大绝对差为 0，作为等价性证据；
该证据不等同于正式 E2 性能结果。

## 请求绑定

以下是负责人签发授权时必须逐字绑定的五项 SHA256。它们来自当前只读绑定输出和
`final_assets.json`；审批材料本身不产生授权。

| 字段 | SHA256 |
|---|---|
| `final_code_sha256` | `d9969aef9d6a8f271a258828ab030a476f304e3b4945f0f338e50b4b93c1e70a` |
| `protocol_sha256` | `7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab` |
| `calibration_thresholds_sha256` | `3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00` |
| `seed_list_sha256` | `8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946` |
| `experiment_config_sha256` | `ba4a22ae5b1fd52cf27b3374aa59200c9550f380a2c6dc0ef679861ebe41d66f` |

当前只读输出明确为 `authorized=false`。负责人签发前不得使用旧绑定，也不得把本申请文件当作授权回执。

## 计划中的 E2 范围

- 正常组 200 个 Seed：`141420000`–`141420199`。
- 攻击组 200 个 Seed：`141430000`–`141430199`。
- 每个 Seed 保留同一健康轨迹下的 8 个候选事件和年龄 32、64、96；统计独立单位仍为 Seed。
- 主门槛场景为事件 `(0, 200)`、Replay age=64，检测窗口 211–216，决策时刻 216，目标状态 217。
- 三种冻结方法为 Hard GLS、Soft Average、Set-based，共同动作上限 `U=0.051261`；不重新校准、不改变协议或门槛。
- E2 只评价集合覆盖、非零动作和正常误动作；E2 通过不会自动授权或启动 E3。

## 负责人签发格式

请负责人独立生成新的 JSON，至少包含：

```json
{
  "authorized": true,
  "scope": "E2",
  "owner": "<负责人身份>",
  "authorization_id": "<唯一编号>",
  "issued_at": "<签发时间>",
  "bindings": {
    "final_code_sha256": "d9969aef9d6a8f271a258828ab030a476f304e3b4945f0f338e50b4b93c1e70a",
    "protocol_sha256": "7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab",
    "calibration_thresholds_sha256": "3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00",
    "seed_list_sha256": "8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946",
    "experiment_config_sha256": "ba4a22ae5b1fd52cf27b3374aa59200c9550f380a2c6dc0ef679861ebe41d66f"
  }
}
```

这段仅为签发格式示例，不是已签发文件；当前仓库不创建 `authorized=true` 文件。

## 获批后的启动接口（本阶段不执行）

负责人提供有效 JSON 后，且仅在运行器重新核对五项绑定、环境指纹和分支代码后，才可执行：

```powershell
$py = 'C:\Users\zhongxin\shixidoc\mypaper\.venv\Scripts\python.exe'
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli `
  --formal-e2 `
  --authorization '<负责人签发的 E2 JSON 绝对路径>' `
  --out 'reviews/g1r_risk_constrained_recovery/results/g1r_e2_run_<唯一RunID>'
```

本阶段未执行该命令，也未创建 Run 目录或正式轨迹。

## 失败、中断和恢复规则

算法合法拒绝（如 `INPUT_INVALID`、`MODEL_INVALID`、`EMPTY_UNION`、`ZERO_OR_UNRESOLVED`、
`SOLVER_REJECT`、`ZERO_PROPOSAL`、`GATE_REJECT`）保留样本分母并记录零动作。
模型/数据生成、Yang 仿真、Replay 来源或年龄、非有限创新、未预期 Proposal 异常、在线/离线写入、
checkpoint 或结果损坏均中止当前 Run，保存堆栈和已完成证据，标记
`ABORTED_INCONCLUSIVE`，不换 Seed、不跳过场景、不发布 `gate_counts`。
进程中断只能在原授权、原配置、checkpoint 哈希一致时恢复同一 Run；异常 Run 不能作为 E2 Go/No-Go。

## 当前审批结论

P0 审计材料完整，具备提交负责人审核的条件；正式授权尚未签发。因此本阶段结束状态为
**PENDING_OWNER_SIGNATURE**。在收到负责人明确批准和五项绑定完全一致的有效 JSON 前，保持停止，不执行 E2 或 E3。
