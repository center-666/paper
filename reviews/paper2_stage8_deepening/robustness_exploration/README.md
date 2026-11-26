# Stage 8 失配稳健性探索

所有新增代码、注册、逐轨迹数据、汇总、图和报告仅写入本目录。主算法和冻结确认数据保持原样。随机记录由 Stage 8 原有生成规则重建，启动前的自检逐项匹配三条冻结基线记录。

## 复现入口

在仓库根目录执行：

    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/reproduce.py --workers 6

逐阶段断点续跑也可使用：

    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py quantization --workers 6
    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py drift --workers 6
    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/run_exploration.py model_mismatch --workers 6
    uv run --python 3.14 --with numpy,scipy,matplotlib python -B reviews/paper2_stage8_deepening/robustness_exploration/rebuild_report.py

输出文件按唯一场景、冻结组和轨迹编号保存。脚本遇到登记哈希不匹配会停止。失败记录单独写入 data/<experiment>/errors/，修复算法或参数后需要创建新注册与独立结果目录，不覆盖已有确认数据。

## 预先登记的协议

registration.json 固定了源文件哈希、运行时、随机数规则、三档健康门限、模型参数、量化定义、漂移率、摄动档、样本量和工作进程数。

- 量化每档使用强正、强负、健康各 12 条，共 216 条，包括连续基线和可选 4 bit。
- 漂移使用 6 个衰减幅度各 12 条。上限截断使正向增强 5 个幅度都等同常值路径，按别名复用同一批随机轨迹，不重复消耗计算。
- A 矩阵摄动 7 档，每档健康、强正、强负各 12 条，共 252 条。
- 同一实验条件下 M0、M1、M2、M3 及 h0/q95 门限动作分支读取同一接收记录。不同位宽或模型参数使用相同外生随机种子索引，但事件历史会随接收载荷和预测中心反馈变化。

证书失配的风险下界计数是诊断量。量化、时变偏置和真实模型摄动均超出原连续载荷、恒定幅值、标称参数证书的理论合同。M3-rho 明确只代表下游支撑扣减机制实验，不提供上游似然证书的变幅概率保证。
