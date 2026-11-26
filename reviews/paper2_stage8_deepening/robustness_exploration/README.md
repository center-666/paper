# Stage 8 失配稳健性探索

所有新增代码、中间数据、图和报告仅写入本目录。主算法和冻结确认数据不作修改。随机记录由 Stage 8 的原生成规则构造，运行前自检强正、强负和健康三条轨迹与冻结记录逐项相同。

## 复现入口

在仓库根目录执行：

    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_matrix_batches_v4.py

完整量化扫描已在第一版登记 registration_v1.json 下完成，原始记录位于 data/quantization/。第一版漂移计算成本过高，未完成记录保留在 data_v1/drift/。优化后的漂移与矩阵摄动漂移输出写入 data_v2/。矩阵摄动使用当前 registration.json，每个 epsilon 与工况将 12 条分成 0–5、6–11 两批，每批 6 条，输出写入 data_v3/。此前 V2 超预算先导尝试保存在 data_v2_attempt/，不混入汇总。V3 +5% 健康档的 Decimal 溢出失败保留于 data_v3/model_mismatch/errors/。V2 失配试跑及已完成文件保存在 data_v2_attempt/，不进入最终统计。最终汇总运行 rebuild_report_final.py。

矩阵摄动单批续跑示例：

    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py model_mismatch --scenario eps_+1.00% --group strong_positive --index-start 0 --index-stop 6

漂移续跑：

    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py drift --workers 6
    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py model_mismatch --workers 6
    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/rebuild_report_final.py

实现、输入或注册哈希不符时脚本会停止。失败轨迹按批次写入 data_v2/drift/errors/ 或 data_v3/model_mismatch/errors/，保留其种子、场景和错误记录。

## 配置与样本

registration_v1.json 固定了量化批次的源哈希、随机规则、三档门限和量化器。连续基线、12、10、8、6、4 bit 各包含强正、强负和健康工况各 12 条，共 216 条。

registration_v2.json 固定优化版漂移批次。registration_v3.json 固定标准 Decimal 指数范围的 0%、±1%、±2% 矩阵摄动。当前 registration.json 固定扩大 Decimal 指数范围后的 ±5% 极端边界探索，每组取索引 0、1。双容对象使用 Z=2、b_max=0.35 cm、查询时刻 127/255/383/511，608 拍记录，损失窗口 [50,561]。幅值门限 h0、q95 和 M1 完整精度均在 JSON 中。各组共享 NumPy SeedSequence([base_seed, frozen_group_index, trajectory_index]) 规则。

漂移幅度从 +0.35 cm 下降到 b_max 区间内。按题设的增强定义从 +0.35 cm 出发会立即饱和为常值，报告只将其作为别名路径。A 摄动使用逐元素 A_plant=A_nom*(1+epsilon_A)。所有在线算法与触发中心仍使用标称系统。

量化、漂移与矩阵摄动都超出连续载荷、恒定偏置或标称参数证书的原始理论合同。其违约数是明确标注的失配代理诊断。M3-rho 只检验下游方向支撑扣减机制，不表示上游时间一致似然证书已扩展为变幅攻击保证。








