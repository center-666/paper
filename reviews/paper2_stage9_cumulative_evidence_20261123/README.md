# 第二篇论文阶段九｜累计污染认证与在线校正

阶段九在 V2 二维耦合系统上实现正方向证书的来源绑定、按起点保留多个幅值区间，以及逐拍更新似然上界。输入为可信发送位、记录的量化重构中心和收到的连续载荷。两套恢复器在同一 monitor 轨迹上运行。

- [数学推导](01_theory.md)
- [实验结果](02_results.md)
- [冻结协议](stage9_protocol.json)
- [冻结轨迹回放](replay_summary.json)
- [独立随机试验](fresh_summary.json)

## 复现

使用冻结清单中的 Python、NumPy 和 SciPy 版本。在本目录运行以下命令。运行器校验源码和依赖的 SHA-256。指定阶段已经保存的结果会直接读取。

```powershell
python check_stage9.py
python paired_recovery.py replay --workers 9
python paired_recovery.py fresh --workers 9
python validate_stage9.py
```

从头复算时，在单独的工作树中移开相应模式的结果目录和汇总文件，保留冻结清单。首次重算独立试验时使用原冻结回放汇总作为前置记录。耗时依赖机器及并行调度，定量统计和证书轨迹可在原输入下复核。
