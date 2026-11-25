# 第二篇论文的持续偏置确认实验

[验收报告](reports/acceptance.md) · [预注册](registration.json) · [模型、威胁接口与文献对照](design.md) · [逐轨迹配对表](reports/paired_trajectories.csv) · [证据与运行产物 SHA-256](manifest.json)

## 版本和输入

原工作树头为 `99015ecd`，独立工作树从研究基线 `f0b23fd9499a7cfc2386ce1363a2059ece59a3a4` 创建于 `paper2-stage7-confirmation-20261125`。预注册引用的可执行源码提交为 `9facbdb8`，注册提交为 `0bc2738d`。确认输入在首条新种子运行前推送到 GitHub。结果提交可由 `git log -1 -- reports/acceptance.md` 在本目录定位。

运行环境为 Windows 11、Intel Core Ultra 9 285H、Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1。图使用 Matplotlib 3.11.2。四进程共用相同的单线程数值库设置，每个进程使用相同八拍暖机。每条轨迹清空纯区间函数缓存。工程延时为这台机器的实测分布。试验不提供硬实时上界。

种子通过 NumPy SeedSequence 派生物理噪声、触发和相位的三个 PCG64 流。健康门限开发用根种子 202611251702；主工况方差与各格成本开发用 202611251703；确认集用 202611251701 和独立的工况、轨迹索引。未跨工况共享随机数。Stage 6–7 根种子 202611226601–6603、Stage 9 的 202611239901 和停止后 Oracle 归档均不作为本轮独立样本。配对只在同一条轨迹内进行。

## 冻结与执行记录

1. 比较 `git diff --stat f0b23fd9 99015ecd`，核对原始 Stage 7 强档 12 条和 Stage 9 早强 3 条。历史配置检查器中的空目录断言仅适用首次采样前。只读原始行复算和确定性夹具以 `code/check.py` 为入口，输出记录于 [audit.json](results/audit.json)。零门限/实际发布位移另在一条既有 Stage 9 历史上复算，见 [h0_archive.json](results/h0_archive.json)。
2. 开发期间先以原始区间评分完成 12 条健康路径，再用相同种子复核快速评分，扩至 200 条。每条最大分数和四个查询分数保存在 [健康校准记录](results/development_point_calibration.json)。校准快路径使用同一物理噪声顺序、精确有理数 Riccati 和二进制浮点网格评分。对三个入选门限附近 \(10^{-8}\) 内的轨迹再用旧 `choose_point` 及 Decimal 评分核读，每次查询以精确十进制分数严格比较。其他秩采用浮点评分，已核验的是边界数值一致性。开发初版把静默噪声写成浮点量，Riccati 对称性断言及时终止；开发时还纠正了分位数单位，四次查询先取轨迹最大值。该过程未使用确认种子。
3. 六条早强开发路径与另外四格各一条用于估算配对标准差和 CPU。六条保存了每次点提议到下一次查询前在评分窗口内的降损，按预冻结主门限取舍这些片段即可给出 M1 的开发差值，因为拒绝会清空待传播幅值。开发过程中补全了传播平局、回退及耗时记账；开发和确认结果分目录。开发记录仅用于规划。
4. 注册冻结五格及固定样本量、绝对时钟、全部对照、窗口、门限、配对区间与顺序检验、目标效应、健康等效容差及数值容差。预算为最多约 4 核时的确认规划值，所有注册 ID 执行完毕作为停止点。详见 [registration.json](registration.json)。
5. 对每个注册 ID 只生成一次公共记录，所有方法消费同一前缀，逐轨迹 JSON 原子写入，已有身份匹配的结果可复用。错误捕获写入 `results/confirmation/errors/`，保留同一编号后重试。确认后的工程计时复用主要工况固定编号 0–3，只测公共记录已经生成后的独立 M1、M3 在线耗时。

## 实际运行命令与复算入口

以下命令均从本目录运行。Windows 实际使用同一已有环境的 `C:\Users\zhongxin\shixidoc\mypaper\.venv\Scripts\python.exe`，这里记为 `python`。独立复跑确认可在注册提交的另一个工作树执行，保留本文结果分支用于比对。确认执行器将在运行前复查源文件、登记的开发输入和随机软件版本。

~~~powershell
python code/check.py
python code/validate_fast_point.py
python code/calibrate_point_gate.py
python code/cutoffs.py
python code/run.py development
python code/timing_dev.py
python code/check_h0.py
python code/register.py
python code/run.py confirmation
~~~

注册脚本用于首次冻结。要精确复现确认集，从 `0bc2738d` 工作树已有的 `registration.json` 直接运行最后一行。确认分支上的 `results/confirmation/*.json` 包含所有方法的配对损失、累计条件改善、算法下界、机会量、四次查询日志、实际有用持续性与每拍新旧下界；一条文件对应一个独立样本。真实状态及参数只用于模拟和离线评分。

一键再生全部统计表、图和中文验收报告的命令如下（从结果分支运行）。独立工程计时已经归档，如需重测可先执行 `python code/profile_methods.py`。

~~~powershell
python code/rebuild.py
~~~

[方法×工况](reports/method_by_case.csv) · [配对主差值及 bootstrap](reports/paired_comparisons.csv) · [四格等权次要汇总](reports/equal_weight_attacks.csv) · [健康不一致事件](reports/health_paired.csv) · [每查询日志](reports/query_log.csv) · [逐轨迹时延](reports/cost_per_trajectory.csv) · [查询级时延](reports/query_cost.csv)
