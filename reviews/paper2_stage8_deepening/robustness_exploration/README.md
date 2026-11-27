# 双容液位实验的失配边界

[中文报告](robustness_report.md) 给出完整分组数据、配对增量和算力口径。[逐轨迹数据](trajectory_metrics.csv) 保存每个方法的损失差、条件改善、动作和审计分母。[配对比较](incremental_comparisons.csv) 给出同轨迹 M3−M2、M3−M1 和衰减档 M3-ρ−M3，并以同编号标称记录复算增量随失配的变化。

## 一键复算

在本目录执行以下命令。默认使用已登记的逐轨迹数据，核对各来源 SHA-256、工况和编号，再生成三个汇总 CSV、配对明细、三张中文 PNG 与报告。

```powershell
uv run --python 3.14.10 --with numpy==2.5.5,scipy==1.18.1,matplotlib==3.11.2,gmpy2==2.3.2 python -B reproduce.py
```

在同一命令末尾加 `--from-seeds --workers 4` 可从种子复跑全部纳入的历史轨迹、稳定参数扫描及独立风险核验，并与逐轨迹归档比较。需要仓库 Git 历史、登记的 Windows Python 与 NumPy 运行时、支持中文的字体。数据分析单独运行只需能读取历史 Git 对象的检出工作区。输出图默认为 320 dpi。报告清单中的文本摘要按 LF 规范化，PNG 按原始字节计算。

## 各批次及分母

| 试验 | 登记与数据目录 | 归档的有效比较 |
|---|---|---|
| 量化 | registration_v1.json，data/quantization | 连续及 12/10/8/6/4 bit，健康、强正、强负各 12 |
| 固定发送前缀的量化复核 | prefix_registration.json，prefix_data | 同一物理状态、事件和中心，仅替换接收载荷。五个位宽各三组各 12，连续档复用原配对轨迹 |
| 漂移 | registration_v2.json，data_v2/drift | 衰减 0/5/10/20/35/50%，各 12。另 60 行增强系裁剪后的常值别名 |
| 整矩阵缩放 | registration_v3.json，data_v3/model_mismatch | 0、±1%、±2%，每档三组各 12 |
| 整矩阵极端缩放 | registration.json，data_v4/model_mismatch | ±5%，三组各 2，只作压力对照。+5% 谱半径大于 1 |
| 稳定水力时间常数 | stable_registration.json，stable_data | 七个档位三组各 12，0% 复用标称记录并独立重放三条，非零档实算 216 条 |

第一版漂移中间记录存于 data_v1/drift，第二版整矩阵试跑存于 data_v2_attempt。标准指数范围下的 +5% 试跑按整个档位退出主统计，data_v3 中的单条成功记录及错误日志均保留，错误日志的本机路径已标为库内相对路径或标准库路径。原注册 JSON 均保留原始身份。

## 关键代码与复核

- `replay_registered.py` 从四次登记的 Git 提交取出计算器，以 `source_layout.json` 还原原始混合换行，逐一比对登记的原始字节 SHA-256。每个版本使用独立进程及对应登记配置。抽样复跑实测见 `replay_samples.json`。
- `audit_drift.py` 对 72 条衰减记录分别走直接滤波与线性污染递推，按每个发送脉冲直接传播核对 M3-ρ 的伴随实现。结果 `drift_oracle_audit.json` 区分 512 拍窗、608 拍全程和严格/带容差下界检查。
- `ablate_direction.py` 在原强正、强负各 12 条上固定 M2 的方向选择，量出仅加入起点—幅值区间的增量，随后量出可在历史方向中择优的边际贡献。输出见 `direction_ablation.json`。
- `stable_sweep.py` 采用稳定的水力弛豫参数族，各方法调用冻结的 `Methods.step`，真值滤波使用 GMP 有理数。损失和健康误动的计算信息分别只提供给离线评分和公开记录接口。
- `rebuild_report_bundle.py` 按登记身份和唯一 ID 加载数据，分别生成真实状态降损、条件风险与有用拍数的配对差。模拟器的单轨 CPU 计时仅累计一次。
