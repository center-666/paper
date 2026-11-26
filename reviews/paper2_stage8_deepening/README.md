# 双容液位确认实验（方案 A）

在本目录可用二进制区间版独立复放全部 116 条双容轨迹。方向选择、连续幅值证书、跨拍传播和发布均从公开帧重算。参考实现的已存动作用于事后对比，真实幅值仅用于离线条件风险核验。

```sh
uv run --script code/binary_query.py --workers 4 --output results/binary_query_audit.json results/confirmation supplement/results/transition
```

[验收报告](reports/acceptance.md) · [逐轨迹配对数据](reports/paired_trajectories.csv) · [三线表](reports/tables/performance.tex) · [工程计时](reports/tables/timing.tex) · [预注册](registration.json)

在本目录执行以下命令可从逐轨迹归档重建报告、图和表。

```sh
python code/rebuild.py
```

首次运行的顺序为 `python code/check.py`、`python code/check_signed.py`、`python code/run.py development`、提交源码和开发结果、`python code/run.py register`、提交注册表、`python code/run.py confirmation`、`python code/timing.py`、`python code/rebuild.py`。已有注册表的独立工作树可以直接运行 confirmation；已有同一注册身份的记录按编号复用。Python、NumPy、SciPy 版本和用于复算的文件哈希见注册表。LaTeX 表使用 booktabs 和支持中文的字体。PDF 为矢量图，PNG 为 320 dpi。

[观测与风险定义](design.md) · [开发强度阶梯](results/development_ladder.json) · [弱档开发核验](results/development_weak.json) · [健康门限定标](results/calibration.json) · [精确递推](results/wp1_checks.json) · [镜像与起点核验](results/signed_checks.json)
