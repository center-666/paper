# E3 准备完成与正式授权申请

状态：**PENDING_OWNER_REVIEW；authorized=false；本轮未启动 E3。**

执行 E2 的授权不适用于 E3。本文件和仓库中的模板/申请 JSON 都不是有效授权。未来必须由负责人另行签发 E3 JSON，并再给出正式启动指令。

## 本轮提交供审阅的结果

| 验收问题 | 结论及证据 |
|---|---|
| E2 独立覆盖复核是否通过 | 通过。4,800 个唯一组合与原记录零差异；[22号报告](22_e2_independent_coverage_audit.md) |
| E3 是否忠实实现冻结协议 | 按既有三算法/门限、真实状态损失、age64最坏事件均值和整Seed Bootstrap实现；[23号说明](23_e3_mathematics_and_implementation.md) |
| 正式数据生成是否具备技术条件 | 碰撞扫描完成、配置/环境/依赖已绑定、43项确定性测试通过；[24号验收](24_e3_preparation_validation.md)。仍缺负责人正式E3授权 |
| 是否发现新错误 | 发现并修复了新统计模块的一处二维索引错误；失败R01保留。最终测试没有未修复失败；没有据此修改冻结算法 |
| 是否可以提交正式授权审批 | 可以提交审核；不代表E3已经获批或性能已验证 |

当前隔离分支：`g1r-e2-status-contract-20261115`。准备工作基于 `9d7384408ab4f55703a9158e613756afa48b088c`；最终准备交付提交SHA以Git提交记录为准，避免在文档内自引用尚未形成的提交哈希。未合并main，未动G5/G2。

## E3 五项绑定

| 字段 | SHA256 |
|---|---|
| final_code_sha256 | `10c3239534c915206c65046ce8f8658e51d1f895b521406d50b8c354859a11ab` |
| protocol_sha256 | `7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab` |
| calibration_thresholds_sha256 | `3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00` |
| seed_list_sha256 | `4da8a054d9991cabfcaed7463696a97aa7445cbe99f7430468b703bb3fb52b4f` |
| experiment_config_sha256 | `e497d60ccaf29d28575984cc2be19d52d461b2f10b4c7f25007b1ec8b938af61` |

[机器可读绑定与47项依赖](results/g1r_e3_preparation_assets_20261116_r04/authorization_bindings.json)记录完整列表。E2结果依赖的主清单为：`artifact_manifest.json` SHA256 `40980383b61a63bc32d026f1db76c2066af7958d27e42792ab1eca27f9b3fd50`；E2 gate摘要为 `86b284409206029aec58a5ab60ca748813aea21c9b3e93cbd84cd10938172e4c`。E3配置还绑定独立覆盖和Seed扫描的结果及明细。任何变更都会影响代码或实验配置绑定，旧授权将失效。

环境沿用Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1与原BLAS指纹 `39fda87a49467f782309e1d07b91b7399217f915b323071f52807b1f59384e87`，不是新设环境。只读入口默认查询绑定，无数据生成。

## 未来执行接口

以下仅说明接口，本轮不执行正式入口：

```powershell
Set-Location 'C:\Users\zhongxin\shixidoc\mypaper_g1r_e2_status_contract'
$py = 'C:\Users\zhongxin\shixidoc\mypaper\.venv\Scripts\python.exe'
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.cli --show-authorization-bindings
# 仅在负责人另行提供E3授权和启动指令后：
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.cli `
  --formal-e3 --authorization '<负责人新签发的E3 JSON绝对路径>' `
  --out 'reviews/g1r_risk_constrained_recovery/results/g1r_e3_run_<负责人批准的唯一RunID>'
```

授权至少包含 `authorized=true`、`scope=E3`、非空负责人身份、唯一E3授权编号、上述五项完整绑定，建议记录签发时间。E2 JSON、旧绑定、空模板或人工构造的非守卫回执均不能通过。仓库内[算法模板](code/g1r_e3_runner/authorization_template.json)和[本次申请](results/g1r_e3_preparation_assets_20261116_r04/e3_authorization_request.json)保持 `authorized=false`。

未来执行前还要检查隔离分支、干净工作区、本地/远程SHA一致、实时环境、五绑定、原E2依赖摘要、Run目录不存在；不得覆盖旧Run。可恢复中断才允许同一授权和Run目录加 `--resume`。`ABORTED_INCONCLUSIVE` 不允许自动恢复，须保留证据交负责人处理。

本轮至此停止：没有正式E3轨迹，没有使用预留Bootstrap Seed，没有有效E3授权文件，也没有真实MSE性能结论。
