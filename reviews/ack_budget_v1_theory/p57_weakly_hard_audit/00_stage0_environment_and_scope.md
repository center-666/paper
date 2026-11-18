# P5.7-0：环境、版本及执行边界

日期：2026-11-18。阶段：仅准备审查对象与文献获取计划。FACT 表示本轮工具核查或已保存来源事实；DERIVED 表示明确来源下的公式转换；OPEN 表示尚未建立证据。

## 1. 阶段结果

**FACT：指定基线检查通过，已从该提交创建独立分支及工作树。P5.7-0 完成后停止，等待负责人审核。** 本阶段不作 P5.7 最终 GO / CONDITIONAL GO / NO-GO 裁决，也不把 P5.6 的 CONDITIONAL GO 自动继承为本轮裁决。

| 项目 | 核验结果 |
|---|---|
| 仓库 | origin = https://github.com/center-666/paper.git |
| 审查基线 | de807527af90f2040e9402fafedc6287dbababa1 |
| 基线工作树 | C:/Users/zhongxin/shixidoc/mypaper_ack_p56_main_claim |
| 基线分支 | ack-v1-p56-main-claim-audit |
| 操作前状态 | `git status --porcelain=v1 --untracked-files=all` 输出为空，HEAD 完全匹配 |
| 远程只读核查 | P5.6 远程分支指向同一提交；查询时不存在 P5.7 同名远程分支 |
| 新分支 | ack-v1-p57-weakly-hard-audit |
| 新工作树 | C:/Users/zhongxin/shixidoc/mypaper_ack_p57_weakly_hard |
| 创建方式 | `git worktree add -b ack-v1-p57-weakly-hard-audit ../mypaper_ack_p57_weakly_hard de807527af90f2040e9402fafedc6287dbababa1` |
| 新工作树初始状态 | HEAD 匹配，工作区干净 |

**FACT。** 当前会话入口目录 mypaper 另有既有研究修改；没有在该目录切分支、清理或写入。本轮选用已有的干净 P5.6 专用工作树作为基线，再创建独立工作树。没有通过清理用户工作区来满足检查。基线工作树及适用父目录未找到 AGENTS.md。

## 2. 必须继承且不重开的结论

以下为 **FACT（已审核 P5.6 的结论记录）**，不是 P5.7 新颖性验证：

| 已有结论 | 原始定位 | 本轮约束 |
|---|---|---|
| 固定截止等待公式降为基础命题 | [P5.6-A](../P5.6_A_fixed_deadline_novelty.md)，A1、A3–A4 | 不恢复独立原创核心地位 |
| C1 独立算法路线停止 | [P5.6 最终报告](../P5.6_final_go_no_go.md)，开头结论、最终边界 | 不复活 C1，不加性能实验 |
| 唯一候选为原协议可达状态分类 | [P5.6-B](../P5.6_B_reachability_novelty.md)，B1–B6 | 仅核对该对象是否被既有理论覆盖 |
| Gaussian 结果是指定模型的物理支持 | [P5.6-C](../P5.6_C_gaussian_physical_relevance.md)，C1–C2 | 不扩大为高频出现或性能收益 |
| 当前不主张通信率或 MSE 优势 | [P5.6-D](../P5.6_D_theory_experiment_alignment.md)，D1 及实验审查 | 不改负结果、不换指标 |

**FACT。** [项目 README](../../../papers/paper2_ack_budget_deadline/README.md)和 [research/current_status.md](../../../research/current_status.md)是较早状态记录。原稿仍有固定截止公式作为贡献候选的历史措辞；本阶段按已审核 P5.6 限定贡献，不修改这些旧文件，不把旧稿措辞当作 P5.7 已通过的结论。

## 3. 本阶段实际读取范围

**FACT。** 核对了 P5.6 最终报告的结论与证据边界、A/B 报告、C/D 的相关模型和范围；读取了 P5.2 原协议与分类证明、自动机 `bounds` / `transitions` / `graph` / `absolute_replay`、保存汇总；逐项对照原稿系统、通信、锚点、门控定义。具体对象及行号见[对象核对](01_original_protocol_object_contract.md)。没有运行旧验证器或仿真入口。

文献工作限于本地目录及 Zotero 题录盘点、Crossref 题录查询、机构记录查询和候选下载地址连通性检查。没有开展 A–E 的全文理论审查；已有摘要与题录不能用于 NOT COVERED 判定。详见[获取计划](02_literature_acquisition_plan.md)。

## 4. 完整性及交付状态

**FACT。** 本阶段仅在本目录新增三份 Markdown 报告及一份证据 JSON。受保护文件包含 P5.2、P5.3、P5.5 全文补录、四份 CN 报告、五份 P5.6 报告、两份 TeX、项目 README 和研究状态，共 58 个文件；分别记录基线工作树、审查工作树初始与结束 SHA256，见 [03_stage0_evidence_and_integrity.json](03_stage0_evidence_and_integrity.json)。Git 差异核验另检查全仓库受跟踪文件，不仅限于该哈希清单。

**FACT。** 未修改旧报告、稿件、算法、配置或数据；未生成轨迹、运行 Monte Carlo、实验或校准；未提交 Git、未推送，旧分支仍在原提交。新分支 HEAD 保持基线，四份新增文件为未提交草稿。

## 5. 停止点

**OPEN。** weakly-hard 理论是否直接给出分类、是否能经简单替换推出禁 101 不变量、剩余增量是否足够发表，均未在本阶段裁决。

下一阶段只有在负责人审核后才开始。届时须取得相关全文，按状态、动作、转移、初态、语言及定理蕴含逐项核对；文献缺页时保持 OPEN。本阶段到此停止，不自动执行 A、B、C、D、E。
