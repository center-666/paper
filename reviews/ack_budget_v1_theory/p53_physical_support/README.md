# ACK-V1 P5.3：正概率物理可达性专项验收

日期：2026-11-18；基准：320744ea77e3f8637980d083e3365d255ac3bb79。
分支：ack-v1-p5-3-physical-support-audit。
本轮仅P5.3，从指定精确基准新建独立worktree；没有继承上一份P53/P6合并分支中的P6内容，没有修改该分支或原工作区。

标签：**FACT**＝原件或完成验证支持；**DERIVED**＝明示条件下推导；**OPEN**＝未解决。

## 最终结论

**DERIVED：ACCEPT（提交研究负责人独立验收）。**
在原五节点二维Gaussian模型、原ACK规则及全部20条边因果贪心攻击下，对每个整数B≥2、L≥B+4，目标边1→2在k=L的决策前以严格正概率到达P5.2指定状态：
\[
\tau=L-1,\ H=\{1\}\cup\{L-B,\ldots,L-2\},\
\gamma_L=1,\quad m^\star=1,\ s_{\rm cost}=0,\
s_{\rm safe}=\min(B-1,L-B-2)>0.
\]
一般性由解析构造、全网正则化和开球证明支持，有限计算仅作核验。

**FACT。** 六组精确有理数见证通过独立完整网络回放：
(2,6)、(2,7)、(3,7)、(3,8)、(5,9)、(5,10)，合计940个边时刻触发判断，零阈值相等；每组均有可复算的7L维原始噪声开球半径。最小案例半径约0.0004253545761，且目标H={1,4}、τ=5、安全等待1、成本中性等待0。

**DERIVED。** 原规则全部可达状态没有严格差距的区域B≤1或L≤B+3仍保持；B=2,L=5负向对照为12个状态、零严格差距。正概率不代表频繁出现，也不代表MSE或长期通信改善。

## 方法要点

先在完整20边网络中反解节点1的新量测，其他节点也实际更新，得到指定目标模式的有理数中心；第二维全部保持0。再用显式有理比例λ<1对全部量测同步缩放。估计和缓存从零初始化、固定分支上的更新是线性的，因此可以证明：原来的高请求仍为高，请求恰落阈值的低分支会进入严格低侧。

随后在完整原始噪声ζ∈R^(7L)上逐行传播线性系数，给出保守正有理半径，有限步归纳保证全部20边触发、原发送规则和贪心阻断模式不变。Gaussian原始噪声正定协方差使此非空开球严格正概率。

## 报告与复现

1. [模型、时序、概率空间](01_model_and_scope.md)
2. [一般参数量测构造及最小案例表](02_parameterized_measurement_witness.md)
3. [全网正则见证与显式开球](03_regular_witness_and_open_neighborhood.md)
4. [正概率定理与完整证明](04_positive_probability_theorem.md)
5. [攻击因果性与全部预算](05_adversary_causality_and_budget.md)
6. [独立验证、数据与限制](06_independent_validation.md)
7. [最终决定与五问答复](07_final_decision.md)

仓库根目录运行（仅Python标准库）：

    python -B reviews/ack_budget_v1_theory/p53_physical_support/code/construct_physical_witness.py --verify
    python -B reviews/ack_budget_v1_theory/p53_physical_support/code/independent_verify_witness.py
    python -B reviews/ack_budget_v1_theory/p53_physical_support/code/verify_integrity.py

data/B2_L6_witness.json、parameterized_witnesses.json保存全部节点估计、20边缓存/残差/裕度/触发/ACK/失败历史及原始噪声系数范数证书。原始分数以字符串保存；十进制仅用于展示。
独立验证使用稀疏线性表达式，未导入主构造或旧引擎；还验证40组负向参数的2692个符号状态，并拒绝4类人为损坏记录。

integrity_manifest.json为新增SHA256清单；data/baseline_file_manifest.json.gz记录基准全部35,124个跟踪文件的路径、Git blob和blob内容SHA256；task_source_manifest.json记录任务附件SHA。校验用Git属性规范化后的diff核查工作树，因此会正确识别Windows core.autocrlf造成的.gitattributes CRLF检出差异；不是声称原始工作树字节与Git blob都相同。本轮所有旧文件在Git规范化视图中均无差异。
本轮没有MC、正式Seed、正式实验Run、估计性能实验或P6。一般有理构造是明确授权的有限确定性见证，不声称实验概率或性能。
