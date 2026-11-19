# P1-B Task A：增益与协方差审查

## 核查对象与结论

**FACT** 审查基线为 `b9d307caf4e07dc3f78abe670ce75ddde9a39d8a`，分支 `watermark-y5-p1`，开始时工作区干净。代码见 [`simulation/model.py`](../../../simulation/model.py#L42)，参数见 [`simulation/config.json`](../../../simulation/config.json#L5)。

**FACT** Yang et al., “Stochastic sensor activation for distributed state estimation over a sensor network,” *Automatica* 50 (2014), 2070–2076，DOI 10.1016/j.automatica.2014.05.025。核读全文第 2071–2073 页：式（3）是估计器，式（8）–（10）给出局部 MSE 增益，第 2072 页明确定义 `P_i,s = E[e_i e_sᵀ]`。本地全文 SHA256：`098034662d93cdaa0e1816d71544cd07115867a4d8d45f46b51416ddf479635c`。PDF 未复制到仓库。

## 一般矩阵增益

令 `e=col(e_1,...,e_N)`，`P=E[eeᵀ]`，`B=(I−εL)⊗A`，`H_b=blockdiag(H_i)`。在全链路同步、节点全激活 `q=1` 下，第 i 个预测误差块是 `Σ_j B_ij e_j`。本地量测创新为 `−H_i e_i+v_i`，其预测误差互协方差为：

```text
Cov(Σ_j B_ij e_j, e_i) = Σ_j B_ij P_j,i = (B P)_i,i.
```

由局部线性 MMSE 正规方程得到：

```text
K_i = (B P)_i,i H_iᵀ (H_i P_i,i H_iᵀ + R_i)⁻¹.
```

这与 `nominal_gains()` 第 45–70 行实现相同；第 66 行的转置线性求解等价于右乘对称创新协方差的逆。**DERIVED** 这是给定全同步预测块与本地创新时的局部 LMMSE 增益。

对于无向邻接图、邻居集合 `N_i`、度数 `d_i`，代码公式展开为：

```text
(B P)_i,i = A[(1−ε d_i)P_i,i + εΣ_(s∈N_i) P_s,i].
```

Yang 2014 印刷式（9）在第 2072 页则写为：

```text
K_pi* = q A{P_i + q εΣ_s(P_i,s − P_i)} H_iᵀ M_i⁻¹,
M_i = q H_i P_i H_iᵀ + q R_i,
P_i,s = E[e_i e_sᵀ].
```

取 `q=1`，印刷式使用 `P_i,s`；由堆叠协方差和预测误差推导出的代码式使用 `P_s,i`。二者在一般非对称交叉协方差下不同。

## 确定性矩阵复核

**NUMERICAL** `verify_p1b.py` 使用五组非对称 2×2 矩阵 `H_i` 和非对角正定 `R_i`，确定性递推检查索引：

- 代码增益与独立的 `(BP)_i,i H_iᵀ S_i⁻¹` 误差：`1.11×10⁻¹⁶`。
- 联合协方差显式装配与 `nominal_gains()` 误差：`2.78×10⁻¹⁷`。
- Yang 印刷式（9）与代码一般矩阵增益最大差：`8.81×10⁻⁴`。
- 测试中 `P_i,s−P_s,i` 最大差：`7.26×10⁻⁴`。
- 全局协方差仍满足 `P_i,s=P_s,iᵀ`；这不蕴含 `P_i,s=P_s,i`。

**NUMERICAL** 冻结 Baseline-Y5 的 `A,Q,P_0,H_i,R_i` 都是标量乘 `I_2`，且拓扑无向。400 步内交叉协方差块具有标量单位阵形式，方向差最大为数值零。因此冻结参数下两种索引一致；这不证明代码的一般矩阵扩展是 Yang 印刷式的字面推广。

## 联合协方差递推

误差定义为估计减真值；过程噪声在节点间共享，节点量测噪声彼此独立并独立于状态，则：

```text
e_(k+1) = F_k e_k + K_b v_k − (1_N⊗I)w_k,
F_k = B − K_b H_b,
P_(k+1) = F_k P_k F_kᵀ + (1_N 1_Nᵀ)⊗Q + K_b R_b K_bᵀ,
K_b = blockdiag(K_i), R_b = blockdiag(R_i).
```

`model.py` 第 55、56、60–70 行实现该递推。**DERIVED** 独立显式组装与代码递推在上述一般矩阵确定性测试中一致。

## 裁定与开放项

- **FACT** 冻结 Baseline-Y5 的标量各向同性矩阵下，P1-A 使用的增益索引一致。
- **DERIVED** `nominal_gains()` 是一般矩阵情形下自然的局部 LMMSE 公式。
- **FACT** 一般矩阵中代码使用 `P_s,i`，Yang 印刷式（9）按其定义使用 `P_i,s`，两者存在方向差异。
- **OPEN** 差异是原文仅考虑其对称/对角结构、印刷或推导中的转置问题，还是代码意图采用一般矩阵 LMMSE 推广，当前材料不能裁定；本轮不改模型。
- **OPEN** 后续若采用非对称 `H_i` 或非对角 `R_i`，不能不加说明地称为 Yang 原文一般式的精确实现。
