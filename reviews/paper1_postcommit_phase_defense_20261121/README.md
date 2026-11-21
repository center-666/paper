# 后置随机相位量化防御研究

基准为上一轮量化长期分析提交 `9ed72601`。本目录研究相位在目标载荷攻击提交后抽取的随机反馈量化器。**原正式稿未修改，未修改大修候选，也没有实际向期刊投稿。**

## 结果导航

- [范围、协议时序与限制](00_scope.md)
- [相位平均辨识性与时间一致 TV--MSE 定理](01_phase_averaged_theorem.md)
- [平衡反射攻击的确定性 TV 积分](02_reflection_tv_quadrature.md)
- [冻结检测与估计验收门](03_experiment_gate.md)
- [实验结果与研究裁决](04_experiment_results_and_decision.md)
- [冻结协议](protocol.json)、[实验核心](core.py)、[试验驱动](experiment.py)、[预检结果](preflight.json)
- [确定性积分实现](deterministic_tv.py)、[复算结果](deterministic_tv_checks.json)
- [冻结前已有工作区哈希](protected_before.json)、[样本运行输出](results/run_v1/)、[事后二项检验复算](audit_event_binomial.py)
- [确定性TV积分推导与复算](02_reflection_tv_quadrature.md)、[实验验收门](03_experiment_gate.md)、[实验结果与裁决](04_experiment_results_and_decision.md)
- [研究包最终核验](delivery_validation.json)、[事后二项复算哈希/范围](results/run_v1/exploratory_audit_manifest.json)

核心证明显示，新独立全周期相位把当前预测的量化误差变成与过去条件均匀的变量。相位平均静默概率严格以零估计偏差为最大值，因而可恢复全因果攻击下的有限时域 TV--MSE 上界，并在 \(Q>0\) 时得到常数不依赖时域长度的平均损伤上界。该定理是总体统计性质，不承诺有限样本检测功效，也不表示随机相位会消除已经进入接收估计的损伤。

平衡反射攻击的确定性积分复现了后置相位下严格正的事件位 TV 和联合记录 TV，并保持 \(\delta^2\) 数值尺度。随机样本随后显示，在原小量化精度下检测率接近误报率；理想连续相位的零 TV 残余地板虽在理论上消除，方法目前尚无实用检测或估计恢复证据。新随机相位也改变健康反馈路径，有限相位实现、同步及真实通信成本未验证。

实验代码和协议冻结后才生成cal/test输入；未进行测试集调参。post-hoc二项复算复用同一冻结test输入，没有生成新随机数，另行标注其探索性身份。检出结果不支持启动异常估计器切换或将该方法并入正式稿。研究结果和局限会作为独立研究包提交到当前GitHub分支。

预检中有一次过严的128点均匀中点积分断言未通过，误差为\(9.83\times10^{-9}\)；该近似检查被Gaussian CDF/高阶Gauss检验取代，最终全部确定性预检通过。原失败记录保留在 `preflight_failure.json`，不是实验或理论失败。
