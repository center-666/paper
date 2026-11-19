# 部分观测与可信事件窗口：范围和来源状态

日期：2026-11-19  
基准分支：research-portfolio-journal-review-20261119  
审查对象：部分观测模型、目标时刻后的连续静默事件窗口，以及攻击可达方向与事件不可感知方向的交集。

## 裁决标签

- FACT：已由仓库模型或取得的全文直接支持。
- DERIVED：在明确写出的模型假设下推导。
- CONJECTURE：尚未完成证明的研究命题。
- OPEN：缺少全文、条件或严格证明。
- DISPROVED：所述普遍命题存在模型内反例。

## 本轮固定模型

考虑

\[
x_{t+1}=Ax_t+w_t,\qquad y_t=Cx_t+v_t,
\]

其中有限维高斯初值、过程噪声和测量噪声独立，\(Q>0,R>0,Z>0\)。可信事件由实际预测 \(m_t^-\) 和真实测量决定；攻击者只能在事件已经决定且实际发送后修改载荷，不能修改事件位、可信反馈或静默时的物理测量。目标时刻 \(k\) 和未来窗口长度 \(L\) 固定且有限。记录至少包括目标后验协方差标签和未来事件串；完整接收载荷日志是更丰富的记录，不能与该受限记录混同。

本轮只做解析审查，不修改论文、不运行新模拟、不研究量化或三预算问题。

## 来源状态

### Hu 等 2025：FULLTEXT

全文：Multi-Sensor State Estimation With a Sequential Stochastic Event-Triggered Mechanism, IEEE TSIPN 11, 342–352 (2025), DOI 10.1109/TSIPN.2025.3546477。

本地文件：C:/Users/zhongxin/Zotero/storage/SEZETRJ7/Hu 等 - 2025 - Multi-Sensor State Estimation With a Sequential Stochastic Event-Triggered Mechanism.pdf。

核验信息：11 页；SHA-256 BAB05FC9299D2F5F5CCE39D94BAC600787A6C6F97B0F42530363010D41FA3452。本文的系统为多传感器线性高斯系统，单传感器可不可检测，并通过观测分解和逐测量分量的随机事件触发建立健康 MMSE 估计。

### Liu 等 2024：OPEN

State Estimation with Event Sensors: Observability Analysis and Multi-sensor Fusion, SIAM JCO 62(1), 167–190 (2024), DOI 10.1137/22M1539204 的出版社 PDF 入口在本轮仍返回 403，尚未取得可逐式核验的全文。因此本报告不从摘要推断其定理，不将其标为已排除直接覆盖。

## 本轮最终问题

未来静默窗口的联合概率是否能产生一个关于目标偏差 \(D_k\) 的正定二次统计证书？若单窗口观测矩阵有零空间，是否必然存在合法零 TV 正损伤攻击？后一个“必然”命题在当前攻击权限下是错误的；需要把普通可观测性替换为攻击可达集合上的条件。
