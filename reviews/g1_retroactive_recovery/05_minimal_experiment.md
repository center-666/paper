# 实验结果及证据撤回（2026-11-13）

最终P0运行：
[g1r_p0_verified_20261113_v1](results/g1r_p0_verified_20261113_v1)。
完整配置、seed、源哈希、全部状态/缓存分量、正常误修正MSE见该目录。
方法/时序与边界见[07](07_full_horizon_propagation_audit.md)、
[08](08_information_permission_audit.md)。

## 现象与修正边界

五节点原异质模型，gap8公共日程，单边0→1，r=200、q=208、d=216、T=280。
恢复窗状态217–260，MSE是状态平方范数和，网络再平均5节点，没有除以状态维数2。
健康receiver/network MSE=0.206899/0.184455。
未保护Replay恢复excess=0.816381/0.244695，单次FDI=0.000719/0.000485。
后续未篡改sender包仍能带网络反馈污染，已在全时域独立差分中验证。

旧minimal_screen_02里receiver drop-and-replay恢复excess约0.146311，
本地滤波checkpoint基线约0.062821；它们基于固定实际入包日志继续运算，
没有让校正回写后重建其他节点发送，不能称为全网闭环恢复。
本轮标准GLS同样只形成影子输出；全网影子结果是离线评价。

## 合法缓存A/B对照

沿用64训练、48校准、48测试seed；ridge=.02，正常95%分位数。
A为本地innovation，B增加实际收到的aligned cache分歧；事件边/时刻oracle已知。

| Replay影子输出 | receiver excess | network excess | normal误修正率 |
|---|---:|---:|---:|
| full A | -0.003048 | -0.001216 | 4.17% |
| full B | 0.000074 | 0.000051 | 6.25% |
| post A | 0.009752 | 0.002766 | 2.08% |
| post B | 0.000875 | -0.000462 | 0% |

同窗口B-A接收MSE配对区间：full[-0.002718,0.008963]，
post[-0.017907,0.000154]，均跨零。FPR未匹配，不能公平排名；
full17拍与post8拍不能用MSE声称结构优越。样本重复研究且无多重校正。
标准GLS同窗递推等价batch的旧代数结论保留，但不构成新机制或Deghat复现。

特征新增消息0字节，原通信179次广播/358边包/5728字节；
full A/B历史272/544B，post A/B为128/256B，拟合矩阵成本见08。
稠密白化仍需历史，不能称全算法仅48B。全网修正广播和内部回写未实现。

## 失败及旧数值状态

| Run | 状态 |
|---|---|
| mapping_01/02 | 循环式核验；原JSON伪CSV保留 |
| mapping_03 | 回灌实际sender差，不独立 |
| mapping_04 | 独立但仅r..q-1；不验证q后 |
| mapping_05 | 导出失败 |
| mapping_06 | 全时域但per-seed扩展名错误 |
| mapping_07/08 | 全时域中间记录，最终入口已更新 |
| output_channels_01 | 未启用分歧分支 |
| output_channels_02 | augmented读取未发送sender状态，仅作额外信息对照 |
| 本轮output_channels_04–07 | 缓存来源合法，但响应矩阵方向错，修正MSE撤回 |
| p0_final_audit_02–05 | 漏查响应矩阵，完整P0 PASS撤回 |

最终Run在计算MSE前核验两单位方向响应；全时域节点/缓存差最大2.31e-13。
所有旧Run均保持原样；正确格式副本位于g1r_format_repair_20261113_v1，
含原文件哈希，格式修复不恢复旧科学有效性。不将多次重跑合并为独立样本。
