# 图件与记录来源

`build_figures.py` 用 Matplotlib 从冻结 JSON 生成三幅图的 410 dpi PNG 和矢量 PDF，并输出逐点和分组 CSV。`same_certificate.py` 在两条预注册轨迹的公开前缀上复放冻结方法，再单独传播最近一次查询的最高等级证书，用有理数核对最终发布动作和风险下界。从本目录执行：

```powershell
python -B build_figures.py
python -B same_certificate.py
```

**图 1** 拟用图题为“随机触发与输出端校正的信号通路 / Signal paths for stochastic triggering and output correction”。下行中心由标称监视器生成。上行载荷仅在发送时存在。轨迹图与敏感度图采用线型和标记同时编码。

**图 2** 拟用图题为“同一方向证书在发送拍后的发布下界 / Published lower bounds following transmission under a common directional certificate”。取强正、强负组各自最小编号 00。评分窗为第 50 至 561 拍，横轴采用从零开始的原始时间标号。先搜索上一拍 M2 有用、当拍发送且无新查询、当拍 M2 下界恰为零且 M3 下界达到 0.000625 cm² 的时刻。再统计同一条件下无新查询的连续有效时长（后续拍可发送或静默）。强正、强负各有 10/20、7/20 条路径至少满足一次。灰区为所选记录上首次出现的分离窗口。`separation_points.csv` 保存绘图数据，`separation_cases.csv` 保存入选时刻和整组分母。

`same_certificate.json` 保留同一方向来源回放。强正 00 的首证在第 383 拍，图中证书在 511 拍签发；强负 00 的首证与图中证书均在 383 拍签发。单独以该证书限制每个候选起点的恒定幅值，逐拍使用冻结实现的同一伴随方向、相同归一化、向内限幅与发布审计。在两条轨迹的分离拍，程序穷举实际 M3 已存方向，核验了唯一产生所选动作和精确下界的方向。515–558 拍（强正）、386–400 拍（强负），单证书回放与归档 M3 的发布动作、下界逐拍相等。正负两个短记录图用于事后机理解释。

**图 3** 拟用图题为“载荷量化及偏置衰减下的有用校正时长 / Useful correction duration under payload quantization and bias decay”。量化使用 registration_v1 与 data/quantization，漂移使用 registration_v2 与 data_v2/drift。每组每档 12 条，共用基线的种子及轨迹号。对线上标称 M3，图中纵轴是整个 512 拍评分窗内达到门限的平均拍数。正偏置从 0.35 cm 开始，在 511 个间隔内匀速衰减，横轴百分比指全窗总跌幅。增强支路从上界出发并立即饱和，统一沿用恒值结果。两幅子图沿用相同的强正编号，不增加独立样本。

`sensitivity_pairs.csv` 给出各档与本组连续／恒值基线之间的每轨有效拍数差的均值及描述性双侧 95% 配对 t 区间。统计独立单位是轨迹。风险核验对全部 608 拍累计检查所有报告正下界的 M3 动作，按原代码对离线改善使用 1e-10 容差；有限比特与变幅工况中的该量是模型失配代理指标。50% 衰减时的 90 次违约集中在 2/12 条独立轨迹，检查分母为 1,478 个动作；0% 至 35% 各测试档均为零次，分母列于 CSV。样本仅支持登记点上的经验差异。
