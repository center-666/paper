# Paper 1：全因果窗口损伤界与逆命题闭合审查

**数学任务完成：充分定理 PASS；逆命题 DISPROVED。一般必要充分条件及新核心贡献仍 OPEN。**

本轮发现全策略充分界和因果分叉反例已存在于旧提交 2e04e439，故交付定位为恢复、复核及纠正近期报告的遗漏，不作为首次发现。不修改论文，不运行新实验。

## 报告索引

1. [范围、来源与更正](00_scope_provenance_and_corrections.md)：旧成果归属、前两轮报告的逐项校正。
2. [全策略上界完整证明](01_all_causal_strategies_bound.md)：扩充信息域、偏差矩阵、统一常数、Gaussian 静默积分与协方差项。
3. [逆命题反例](02_inverse_disproved_by_causal_branching.md)：核方向正概率可达，但全部合法策略仍有线性 TV—MSE 界。
4. [零 TV 等价与单拍边界](03_zero_tv_characterization_and_single_shot.md)：最小记录准确刻画、单拍完整事件串同律、二维定量 TV。
5. [最终裁决与证据自查](04_decision_and_evidence_audit.md)：独立增量、文献状态和停止建议。

## 关键结论

固定模型、有限 \(k,L,b_{\rm ref}\)，若所有事件历史上
\[
\ker G_L\cap{\rm range}B_{k,h}=\{0\},
\]
则全部允许历史/量测相关有界因果策略满足
\[
J_k(\pi)\le (M_*/q_*+\Omega_k)
{\rm TV}\bigl(\mathcal L_\pi(P_k^+,1_{E_L}),\mathcal L_0(P_k^+,1_{E_L})\bigr).
\]

反过来不成立。02 的二维相关先验例子中，\({\rm range}B_{1,11}=\mathbb R^2\)，不可感知方向也可由合法策略在历史 \(11\) 上实现；但历史 \(10\) 的正概率静默会暴露此前动作，故零记录 TV 强制 \(J_1=0\)。

对最小记录，无需秩条件即可得
\[
\Delta_L=0\iff
\bigl[\mathcal L_\pi(P_k^+)=\mathcal L_0(P_k^+)
\ \text{且}\ G_LD_k=0\ \pi\text{-a.s.}\bigr].
\]
此等价没有解决共同因果策略的存在性，不能宣称一般结构性必要充分定理已完成。

## 验证资产

- [精确有理数核查脚本](check_exact_algebra.py)
- [代数断言结果](exact_algebra_checks.json)
- [保护资产修改前哈希](protected_sources_before.json)
- [保护资产及文件验证结果](delivery_validation.json)

唯一下一步建议：恢复现有稿件的定稿终校。本轮到此停止。
