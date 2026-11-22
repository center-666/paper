# 阶段五：污染认证时间与计算结构

基准ccc18e09，日期2026-11-22。完成理论推导、外向数值证书及确定性实现检查；**零新增性能随机样本，正式稿未修改**。

## 主要结果

- 证明精确起点候选在每个移动零点分段上具有至少 \(1/S_{\max}\) 的强凹曲率，缓存A/B/H并实现安全切线上包络。
- 核查逐历史Hellinger信息时钟的鞅及任意时刻错误候选保留界，明确当前中心与当前载荷的先后滤过。
- 用有界复特征和外向参数区间，把强档有限字典所需的三类核对统一缺口认证到 \(10^{-4}\)。六个完整连续参数域，共27,568叶箱，全部逐叶重算。
- 相同风险合同下，充分攻击年龄从S1 4,398,227拍、U1 4,813,844拍，收紧至**255,199拍、252,346拍**。

这不是实际恢复延迟，也没有达到512–2048拍保证。用户提供的约0.0046探索缺口未被本包认证；本轮得到的是较保守但可复查的新界。

## 文件

- [范围与来源](00_scope_and_provenance.md)
- [分段强凹性与认证程序](01_piecewise_strong_concavity.md)
- [信息时钟与合法条件化](02_information_clock.md)
- [亲和度恒等式与有界特征证书](03_affinity_and_feature_certificates.md)
- [结果、计时与限制](04_results_and_limits.md)
- [缓存认证器](strong_concavity.py)、[296项确定性检查](optimizer_checks.json)
- [公式核查](analytic_checks.json)
- [参数域认证程序](certify_fourier.py)、[逐叶重放程序](verify_fourier.py)
- [全域证书及叶箱](fourier_certificates/)
- [新时间界](new_time_bounds.json)、[100位独立复算](independent_time_checks.json)
- [交付核验](delivery_validation.json)

## 复现

基础程序使用Python标准库Decimal，继承上一阶段50位区间算术。主认证例：

    python certify_fourier.py --model S1 --gap .15 --target .0001
    python verify_fourier.py --model S1 --gap .15 --target .0001

对S1/U1和三个差值.15/.2/.25分别执行，所有树验证通过后执行update_time_bound.py与check_time_independent.py。check_optimizer.py只运行固定记录；check_analytic_formulas.py另需NumPy 2.4.6、SciPy 1.17.1。inspect_fourier.py只是确定性局部探索，不参与认证接受决策。

固定记录的重复评分约快1.24–1.54倍，但缓存预处理可能抵消收益；不宣称整套在线算法已更快，也不宣称MSE实测下降。中心/连续载荷、固定同向攻击、模型正确性等前提沿用阶段四；仅码字或有限字长投影需重建概率核。
