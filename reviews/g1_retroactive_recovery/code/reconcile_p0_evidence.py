"""Remove superseded claims; retain every raw result and original Git history."""
from pathlib import Path
import json
import hashlib
import csv

B=Path(__file__).resolve().parents[1]
FINAL=B/"results/g1r_p0_verified_20261113_v1"
assert json.loads((FINAL/"acceptance.json").read_text(encoding="utf-8"))["status"]=="PASS"
revoked=("g1r_deghat_mapping_audit_20261112_04",
         "g1r_deghat_mapping_audit_20261112_03",
         "g1r_deghat_output_channels_20261112_02")
note="""
## 2026-11-13 P0最终审计修订（当前结论）

最终有效证据为g1r_p0_verified_20261113_v1，见07、08与p0_acceptance。
mapping_04虽自行递推但只到q前，原全时域声明撤回；q后差异原先只来自完整仿真观察。
output_channels_02的augmented组读了未通信时刻sender内部状态，只能作为额外信息对照。
本轮中间output_channels_04–07使用合法缓存，却因响应矩阵左右乘错误而导致修正MSE失真；
p0_final_audit_02–05漏检该错误，PASS结论撤回。所有旧结果原样保留，不合并样本。

最终Run独立预测r=200到T=280的节点和缓存全部分量，最大误差2.31e-13；
两个单位方向的响应矩阵也对照完整仿真通过。线上特征只接受本地量测、own estimate、
实际收到的aligned cache和H，不接受run、攻击标签、隐藏sender估计或真状态。
完整窗合法缓存与local的Replay接收MSE配对差+0.003123，
95%区间[-0.002718,0.008963]；后窗差-0.008877，区间[-0.017907,0.000154]。
均跨零且正常误修正率不同，不能称公平性能优势。具体数值、成本和正常MSE见08。

补偿是影子输出扣除，未将校正写回全部节点/缓存，也未实现修正消息协议。
全网影子输出MSE不等于全网部署恢复；事件边/时刻仍已知，SoD闭环未验证。
稠密Cholesky白化仍需历史向量；信息矩阵/得分48B不是整个算法内存。
保留后续量测验证历史数据的基础机制，终止post-cache GLS/influence-capsule独立创新开发。
"""

for name in ("01_literature_gap.md","02_problem_formulation.md","03_candidate_methods.md",
             "04_theorem_candidates.md","05_minimal_experiment.md","06_research_decision.md"):
    p=B/name
    text=p.read_text(encoding="utf-8")
    paragraphs=text.split("\n\n")
    paragraphs=[s for s in paragraphs if not any(key in s for key in revoked)
                and "P0最终勘误" not in s and "P0代码审计修订" not in s
                and "另一个筛选比较把 Deghat" not in s]
    text="\n\n".join(paragraphs)
    text=text.replace("MSE为每状态/节点/时间平方误差均值","MSE为状态平方范数，先按时间再按节点平均")
    text=text.replace("现有五节点系统的 (A=1.01I)","本轮系统A=[[1,.1],[0,1.01]]")
    text=text.replace("最终审计是 03。","最终全时域验证以20261113_v1为准。")
    # Old statistics remain historical evidence, not silently overwritten.
    if name=="05_minimal_experiment.md":
        text=text.replace("## 试验登记","## 初始机制筛选历史记录（输出修正，不是回写）",1)
    p.write_text(text.rstrip()+"\n\n"+note.strip()+"\n",encoding="utf-8")

(B/"p0_acceptance.md").write_text("""# P0最终验收

2026-11-13。唯一最终入口：[acceptance.json](results/g1r_p0_verified_20261113_v1/acceptance.json)。
此前p0_final_audit_02–05漏检响应矩阵方向，完整PASS已撤回。

| 项目 | 结论 | 验证 |
|---|---|---|
| 全时域节点/缓存递推 | PASS | 76800状态分量行、153600缓存分量行，全部≤1e-10 |
| 单位响应矩阵 | PASS | 2个独立方向完整仿真对照，最大<1.89e-13 |
| 合法接收信息 | PASS | 特征函数只有local_y/own/received_aligned/H |
| 时钟/保持/预测 | PASS | 全48seed、clean/FDI/Replay逐时检查 |
| 因果性 | PASS | 未来值置NaN不影响前缀 |
| 原Yang等价 | PASS | logger返回1，与vanilla正常轨迹相同 |
| 新CSV格式 | PASS | 实际CSV写出；旧JSON伪CSV另存格式副本 |
| 公平性能 | LIMITED | oracle定位、FPR未匹配、旧seed复用、影子输出 |
| SoD闭环/全网回写 | NOT TESTED | 未扩展宣称 |

配置、源哈希、拟合表及逐分量数据见最终Run，人工审计见07/08。
保护文件及所有旧Run逐个哈希校验未变。P0通过不是方法新颖性或Deghat复现通过。
""",encoding="utf-8")

# Correct formats at a new path; NEVER replace the legacy pseudo-CSV.
repair=B/"results/g1r_format_repair_20261113_v1"
repair.mkdir(exist_ok=False)
index=[]
for p in sorted((B/"results").glob("g1r_deghat_mapping_audit_*/per_seed_propagation.csv")):
    if not p.read_text(encoding="utf-8-sig").lstrip().startswith("["):
        continue
    rows=json.loads(p.read_text(encoding="utf-8"))
    folder=repair/p.parent.name; folder.mkdir()
    (folder/"per_seed_propagation.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    with (folder/"per_seed_propagation.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows([{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows])
    index.append({"original":str(p.relative_to(B)),"original_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                  "correct_csv":str((folder/"per_seed_propagation.csv").relative_to(B)),
                  "correct_json":str((folder/"per_seed_propagation.json").relative_to(B)),
                  "scientific_validity":"format repair only; does not rehabilitate invalid runs"})
(repair/"index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")
print("Reconciled six reports; preserved legacy results and wrote corrected-format copies.")
