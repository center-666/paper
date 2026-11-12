# 分阶段校准与序贯强基准：验证结果

计划：2026-11-11_steady_fpr_sequential_benchmark；最终测试192个全新种子。每个日程/攻击边/方法/场景都运行并保留，不依据测试结果调参。

**完整贡献门槛：未通过。主要12项对照通过5项，满足全部三基准且外部边无明显退化的场景单元1/4。**

## 实验的实际变化

- 正常缓存周期按起始时刻分为initial、transient、steady，分别拟合；仿真末尾未结束的周期不用于阈值与误隔离率分母。
- 五种检测器共享年龄权重和正常联合协方差。白化窗口、能量CUSUM及双侧分量CUSUM只使用当前/历史合法残差；过去的白化增量不因未来样本到来而回写。
- 各检测器用正常tune数据固定四轮调整至相同5%目标，另用normal_audit和test实测。不是声称任意时间/任意分布都有严格5%保证。
- 核心比较是原攻击边全幅/半幅FDI下mean对三序贯基准；外部边、低幅、Replay和瞬时对照均额外报告，不能替代未通过主要门槛。

## 主要效果

正值表示mean更好。Holm p检验至少1%改善，正常代价/误隔离匹配为预设点估计筛查。

| 日程 | 攻击 | 基准 | 接收节点MSE改善 | Holm p | 正常代价合格 | 门槛 |
|---|---|---|---:|---:|---|---|
| gap8 | step | white_window | +4.883% | 5.274e-05 | True | True |
| gap8 | step | white_cusum | +4.845% | 5.274e-05 | True | True |
| gap8 | step | white_signed_cusum | +2.736% | 0.1189 | True | False |
| gap8 | half_step | white_window | -0.273% | 1 | True | False |
| gap8 | half_step | white_cusum | -0.394% | 1 | True | False |
| gap8 | half_step | white_signed_cusum | -1.035% | 1 | True | False |
| irregular | step | white_window | +8.674% | 4.108e-14 | True | True |
| irregular | step | white_cusum | +7.088% | 5.255e-12 | True | True |
| irregular | step | white_signed_cusum | +6.793% | 4.008e-10 | True | True |
| irregular | half_step | white_window | +0.280% | 1 | True | False |
| irregular | half_step | white_cusum | +0.379% | 1 | True | False |
| irregular | half_step | white_signed_cusum | -0.189% | 1 | True | False |

## 正常误隔离率：审计与最终测试

不使用审计/测试结果再次调门限。以下是整条缓存驻留周期首次误隔离率，分母仅为完整周期。

| 日程 | 方法 | 审计稳态 | 测试初始 | 测试过渡 | 测试稳态 |
|---|---|---:|---:|---:|---:|
| gap8 | instant | 4.765% | 6.615% | 5.116% | 5.011% |
| gap8 | mean | 5.208% | 7.292% | 5.141% | 5.262% |
| gap8 | white_window | 4.754% | 6.094% | 4.662% | 5.024% |
| gap8 | white_cusum | 4.805% | 6.406% | 4.503% | 5.191% |
| gap8 | white_signed_cusum | 4.974% | 5.885% | 4.797% | 5.167% |
| irregular | instant | 4.820% | 6.146% | 4.921% | 5.024% |
| irregular | mean | 5.238% | 6.979% | 4.993% | 5.343% |
| irregular | white_window | 4.868% | 6.823% | 4.514% | 5.007% |
| irregular | white_cusum | 4.870% | 6.510% | 4.582% | 4.961% |
| irregular | white_signed_cusum | 5.135% | 5.729% | 4.974% | 5.256% |

## 外部攻击边的结果

| 日程 | 攻击 | 基准 | mean接收节点MSE改善 |
|---|---|---|---:|
| gap8 | step | white_window | +9.517% |
| gap8 | step | white_cusum | +8.547% |
| gap8 | step | white_signed_cusum | +10.292% |
| gap8 | half_step | white_window | +0.653% |
| gap8 | half_step | white_cusum | +0.393% |
| gap8 | half_step | white_signed_cusum | +0.484% |
| irregular | step | white_window | +8.274% |
| irregular | step | white_cusum | +5.518% |
| irregular | step | white_signed_cusum | +7.774% |
| irregular | half_step | white_window | +1.392% |
| irregular | half_step | white_cusum | +1.169% |
| irregular | half_step | white_signed_cusum | +0.519% |

## 解释限制与复核入口

- 协方差来自共同正常age-only运行；实际非线性防御下分布可能变化，正常门限调节只作有限迭代。
- 白化为估计条件矩下的因果变换，不保证实际运行创新严格独立高斯；门限由正常周期最大值经验校准，不使用错误独立卡方假设。
- 统计独立单位是192种子，不是26,880条方法轨迹；结果条件于拟合的正常参数，不包含训练数据重采样不确定性。
- 正常MSE代价和FPR匹配是点估计接受条件，不是非劣性证明；per_seed_phase_rates按轨迹保存，区间按轨迹聚类bootstrap。
- 这是同一研究架构中的CUSUM/窗口机制对照，不是Tunga2018闭环控制系统完整复现，也不意味着穷尽所有CUSUM参数。
- 初始化初始周期短、样本有限，单独报告后不能与稳态混为一个全时误隔离保证。

[主要效果图](figures/primary_comparisons.png) · [分阶段误隔离率图](figures/phase_false_isolation.png)

数据：plan.json、registration.json、sources/、phase_sample_counts.csv、frozen_controls.json、normal_audit_rates.csv、per_seed_metrics.csv、per_seed_phase_rates.csv、primary_tests.csv、all_comparisons.csv、各方法轨迹NPZ及逐周期CSV。
