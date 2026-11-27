"""Rebuild the Stage B tables, paired comparisons and figures from registered traces."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys
sys.dont_write_bytecode=True
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from scipy.stats import t as student

from replay_registered import source

ROOT=Path(__file__).resolve().parent
GROUPS=("health","strong_positive","strong_negative")
NAMES={"health":"健康","strong_positive":"强正","strong_negative":"强负"}
METHODS=("M0","M1","M2","M3","M1_h0","M1_q95")
PERCENT=(-5,-2,-1,0,1,2,5)
CASES={
    "quantization":["continuous","12bit","10bit","8bit","6bit","4bit"],
    "drift":[f"decay_{x:02}" for x in (0,5,10,20,35,50)]+[f"enhance_{x:02}" for x in (5,10,20,35,50)],
    "model_mismatch":[f"eps_{x:+.2f}%" for x in PERCENT],
    "stable_model":[f"tau_{x:+d}%" for x in PERCENT],
}
BASELINES=("continuous","decay_00","eps_+0.00%","tau_+0%")


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    b=path.read_bytes()
    if path.suffix!=".png":
        b=b.replace(b"\r\n",b"\n")
    return hashlib.sha256(b).hexdigest()


def write_csv(name,rows):
    with (ROOT/name).open("w",encoding="utf8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0].keys(),lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def load_rows():
    groups=defaultdict(dict)
    sources=[
        ("registration_v1.json","data/quantization","quantization"),
        ("registration_v2.json","data_v2/drift","drift"),
        ("registration_v3.json","data_v3/model_mismatch","model_mismatch"),
        ("registration.json","data_v4/model_mismatch","model_mismatch"),
        ("stable_registration.json","stable_data","stable_model"),
    ]
    cost={}
    for reg,folder,exp in sources:
        sha=digest(ROOT/reg)
        used=[]
        for path in sorted((ROOT/folder).glob("*.json")):
            row=read(path)
            assert row["registration_hash"]==sha and row["experiment"]==exp,path
            if folder.startswith("data_v3") and abs(float(row["scenario"][4:-1]))==5:
                continue
            key=(exp,row["scenario"],row["group"])
            assert key[1] in CASES[exp] and key[2] in GROUPS and row["index"] not in groups[key]
            groups[key][row["index"]]=row
            if not row.get("alias_of"):
                used.append(row)
        cost[folder]=(len(used),math.fsum(r["cpu_seconds"] for r in used)/3600)
    # Both stable baselines use the same nominal system. Three independently
    # regenerated ID-0 traces must match the saved data before sharing all 36 IDs.
    for g in GROUPS:
        orig=groups["quantization","continuous",g]
        target=groups["stable_model","tau_+0%",g]
        assert target.keys()=={0}
        assert target[0]["public_history_sha256"]==orig[0]["public_history_sha256"]
        for idx in range(12):
            if idx not in target:
                target[idx]={**orig[idx],"baseline_source":"quantization/continuous"}
    for exp,cases in CASES.items():
        for case in cases:
            cohorts=("strong_positive",) if exp=="drift" else GROUPS
            n=2 if exp=="model_mismatch" and abs(float(case[4:-1]))==5 else 12
            for g in cohorts:
                cohort=groups[exp,case,g]
                assert set(cohort)==set(range(n)),(exp,case,g,len(cohort))
                assert all(r["seed"]==202611252822 and r["horizon"]==608 for r in cohort.values())
                if case.startswith("enhance"):
                    baseline=groups["drift","decay_00",g]
                    assert all(r["metrics"]==baseline[i]["metrics"] and r["public_history_sha256"]==baseline[i]["public_history_sha256"] for i,r in cohort.items())
    return groups,cost


def interval(v):
    avg=st.mean(v)
    if len(v)<3:
        return avg,None,None
    se=st.stdev(v)/math.sqrt(len(v))
    h=float(student.ppf(.975,len(v)-1))*se
    return avg,avg-h,avg+h


def stats(groups):
    summary=[];detail=[];pairs=[]
    audits=read(ROOT/"drift_oracle_audit.json")
    assert len(audits)==72 and sum(r["checked_steps"] for r in audits)==72*608
    audit={(r["scenario"],r["index"]):r["methods"] for r in audits}
    for exp,cases in CASES.items():
        baseline=BASELINES[list(CASES).index(exp)]
        for case in cases:
            for g in (("strong_positive",) if exp=="drift" else GROUPS):
                byid=groups[exp,case,g]
                n=len(byid)
                methods=METHODS+(("M3_rho",) if case.startswith("decay") else ())
                for method in methods:
                    values=[]
                    for idx,row in sorted(byid.items()):
                        m=row["metrics"][method]
                        a=None
                        if exp=="drift" and method not in ("M1_h0","M1_q95"):
                            a=audit[row.get("alias_of",case),idx][method]
                        v=dict(experiment=exp,scenario=case,group=g,index=idx,method=method,
                               seed=row["seed"],source_sha256=row["registration_hash"],
                               public_sha256=row["public_history_sha256"],
                               reuse=row.get("alias_of",row.get("baseline_source","")),
                               rho=row.get("rho"), spectral_radius=row["spectral_radius_A_plant"],
                               sends=row["transmissions"],actual_gain=m["actual_gain"],conditional_gain=m["conditional_gain"],
                               negative_steps=m["conditional_negative_steps"],useful_steps=m["useful_steps"],
                               endpoint=int(m["endpoint_useful"]),first=m["first_useful"],any_action=int(m["false_action"]),
                               checks=m["certificate_checks"] if method in ("M2","M3","M3_rho") else None,
                               violations=m["risk_violations"] if method in ("M2","M3","M3_rho") else None,
                               window_checks=a["window_checks"] if a and method in ("M2","M3","M3_rho") else None,
                               window_violations=a["window_viol"] if a and method in ("M2","M3","M3_rho") else None,
                               full_strict=a["full_strict"] if a and method in ("M2","M3","M3_rho") else None)
                        values.append(v);detail.append(v)
                    total=lambda k:sum(v[k] for v in values if v[k] is not None)
                    avg=lambda k:st.mean(v[k] for v in values)
                    cert=method in ("M2","M3","M3_rho")
                    first=[v["first"] for v in values if v["first"] is not None]
                    summary.append(dict(experiment=exp,scenario=case,group=g,method=method,n=n,
                        actual_gain_mean=avg("actual_gain"),conditional_gain_mean=avg("conditional_gain"),
                        useful_steps_mean=avg("useful_steps"),endpoint_count=total("endpoint"),endpoint_rate=total("endpoint")/n,
                        any_action_count=total("any_action"),health_false_rate=total("any_action")/n if g=="health" else None,
                        first_success=len(first),median_delay_success=st.median(first)-50 if first else None,
                        negative_actual_trajectories=sum(v["actual_gain"]<0 for v in values),
                        negative_conditional_trajectories=sum(v["conditional_gain"]<0 for v in values),
                        negative_conditional_steps=total("negative_steps"),
                        negative_conditional_step_rate=total("negative_steps")/(512*n),
                        certificate_checks=total("checks") if cert else None,risk_violations=total("violations") if cert else None,
                        violation_per_check=total("violations")/total("checks") if total("checks") else None,
                        violation_per_608_steps=total("violations")/(n*608) if cert else None,
                        drift_window_checks=total("window_checks") if cert and exp=="drift" else None,
                        drift_window_violations=total("window_violations") if cert and exp=="drift" else None,
                        drift_strict_violations=total("full_strict") if cert and exp=="drift" else None,
                        spectral_radius=values[0]["spectral_radius"],rho=values[0]["rho"],send_rate=total("sends")/(608*n)))
                for m,j in (("M3","M2"),("M3","M1"))+((("M3_rho","M3"),("M3_rho","M2")) if case.startswith("decay") else ()):
                    reference=groups[exp,baseline,g]
                    pr=dict(experiment=exp,scenario=case,group=g,method=m,reference=j,n=n)
                    for field,label in (("actual_gain","gain"),("conditional_gain","conditional"),("useful_steps","steps")):
                        def diff(r):
                            return r["metrics"][m][field]-r["metrics"][j][field]
                        vals=[diff(r) for i,r in sorted(byid.items())]
                        change=[diff(r)-diff(reference[i]) for i,r in sorted(byid.items())]
                        for prefix,sample in ((label,vals),(label+"_change_vs_nominal",change)):
                            mu,lo,hi=interval(sample)
                            pr[prefix]=mu;pr[prefix+"_lo"]=lo;pr[prefix+"_hi"]=hi
                    pairs.append(pr)
    return summary,detail,pairs


def pick(rows,exp,case,g,method):
    return next(r for r in rows if (r["experiment"],r["scenario"],r["group"],r["method"])==(exp,case,g,method))


def plots(summary,pairs):
    fonts={p.name for p in font_manager.fontManager.ttflist}
    name=next((f for f in ("Microsoft YaHei","SimHei","Noto Sans CJK SC") if f in fonts),None)
    if not name: raise RuntimeError("A Chinese plotting font is required")
    plt.rcParams.update({"font.sans-serif":[name],"axes.unicode_minus":False,"font.size":9,"axes.spines.top":False,"axes.spines.right":False})
    folder=ROOT/"figures";folder.mkdir(exist_ok=True)
    def save(fig,name):
        for ax in fig.axes:
            ax.grid(axis="y",ls=":",color=".8",zorder=0)
        fig.savefig(folder/("fig_"+name+".png"),dpi=320,bbox_inches="tight")
        plt.close(fig)
    def pair(exp,case,g,m,j):
        return next(r for r in pairs if (r["experiment"],r["scenario"],r["group"],r["method"],r["reference"])==(exp,case,g,m,j))
    def signed(ax,x,y,negative):
        ax.plot(x,y,"--s" if negative else "-o",color=".35" if negative else "black",
                label="强负" if negative else "强正",markersize=4)
    exp="quantization";cases=CASES[exp];x=["连续","12","10","8","6","4"]
    fig,axes=plt.subplots(1,3,figsize=(11,3.45),layout="constrained")
    for g in GROUPS[1:]:
        ps=[pair(exp,c,g,"M3","M2") for c in cases]
        rs=[pick(summary,exp,c,g,"M3") for c in cases]
        for ax,y in zip(axes,([r["gain"] for r in ps],[r["steps"] for r in ps],[100*r["violation_per_check"] for r in rs])):
            signed(ax,x,y,g==GROUPS[2]);ax.set_xlabel("接收载荷位宽 / bit")
    for ax,label in zip(axes,("实际降损增量（M3−M2）/ cm²","有用拍数增量（M3−M2）","M3 连续参考违约 / %")):
        ax.set_ylabel(label);ax.legend(frameon=False)
    save(fig,"quantization")
    exp="drift";cases=CASES[exp][:6];x=[0,5,10,20,35,50];g=GROUPS[1]
    fig,axes=plt.subplots(1,3,figsize=(11,3.45),layout="constrained")
    for method,style in (("M2",":^"),("M3","-o"),("M3_rho","--s")):
        rs=[pick(summary,exp,c,g,method) for c in cases]
        for ax,y in zip(axes,([0 if method=="M2" else pair(exp,c,g,method,"M2")["gain"] for c in cases],
                                [r["useful_steps_mean"] for r in rs],[100*r["violation_per_check"] for r in rs])):
            ax.plot(x,y,style,color=".2",label=method.replace("_rho","-ρ"),markersize=4)
    for ax,label in zip(axes,("相对 M2 的实际降损增量 / cm²","平均有用校正拍数","低于标称发布下界 / %")):
        ax.set_xlabel("偏置窗末衰减 / %");ax.set_ylabel(label);ax.legend(frameon=False)
    save(fig,"drift_phase")
    fig,axes=plt.subplots(2,2,figsize=(9.4,6.2),layout="constrained")
    for (exp,title,grid),a in zip((("stable_model","水力时间常数",PERCENT),("model_mismatch","整矩阵缩放（稳定子集）",PERCENT[:-1])),axes):
        cases=[f"tau_{v:+d}%" if exp=="stable_model" else f"eps_{v:+.2f}%" for v in grid]
        for g in GROUPS[1:]:
            rs=[pair(exp,c,g,"M3","M2") for c in cases]
            signed(a[0],grid,[r["gain"] for r in rs],g==GROUPS[2])
        for m,line in (("M1","-o"),("M2",":^"),("M3","--s")):
            a[1].plot(grid,[100*pick(summary,exp,c,"health",m)["health_false_rate"] for c in cases],line,
                      label=m,color=".25",markerfacecolor="none",markersize=5)
        a[1].set_ylim(-2,103)
        a[1].set_yticks((0,25,50,75,100))
        for ax,label in zip(a,("实际降损增量（M3−M2）/ cm²","健康轨迹有动作 / %")):
            ax.set_xlabel(title+"摄动 / %");ax.set_ylabel(label);ax.legend(frameon=False,ncol=2)
    save(fig,"model_mismatch")

def prefix_diagnostic(groups):
    rows=[]
    for path in sorted((ROOT/"prefix_data").glob("*.json")):
        r=read(path)
        assert r["registration_hash"]==digest(ROOT/"prefix_registration.json")
        ref=groups["quantization","continuous",r["group"]][r["index"]]
        assert r["sender_sha256"]==ref["public_history_sha256"]
        assert r["transmissions"]==ref["transmissions"]
        failure=r["failure"] or {}
        m=r["metrics"]
        out=dict(scenario=r["scenario"],group=r["group"],index=r["index"],completed=m is not None,
                 failure=failure.get("reason"),first_rejection=failure.get("t"),offset=failure.get("offset"),
                 clipped_sends=r["clipped_sends"],sender_sha256=r["sender_sha256"],cpu_seconds=r["cpu_seconds"],
                 M3_minus_M2_gain=m["M3"]["actual_gain"]-m["M2"]["actual_gain"] if m else None)
        for name in ("M0","M1","M2","M3"):
            for key in ("actual_gain","conditional_gain","useful_steps","endpoint_useful","risk_violations","certificate_checks"):
                out[name+"_"+key]=m[name][key] if m else None
        rows.append(out)
    assert {(r["scenario"],r["group"],r["index"]) for r in rows}=={(c,g,i) for c in CASES["quantization"][1:] for g in GROUPS for i in range(12)}
    write_csv("fixed_prefix_diagnostic.csv",rows)
    return rows


def number(x,d=4):
    return f"{x:.{d}f}" if x is not None else "—"


def ci(r,field):
    return number(r[field]) if r[field+"_lo"] is None else f"{number(r[field])} [{number(r[field+'_lo'])}, {number(r[field+'_hi'])}]"


def report(groups,cost,sums,pairs):
    text=[]
    def paragraph(s): text.extend([s,""])
    def table(headers,body):
        text.append("| "+" | ".join(headers)+" |")
        text.append("|"+"|".join("---" for _ in headers)+"|")
        for line in body: text.append("| "+" | ".join(map(str,line))+" |")
        text.append("")
    def contrast(exp,case,g,m="M3",j="M2"):
        return next(r for r in pairs if (r["experiment"],r["scenario"],r["group"],r["method"],r["reference"])==(exp,case,g,m,j))
    def row(e,c,g,m="M3"): return pick(sums,e,c,g,m)
    def fraction(r): return f"{r['risk_violations']}/{r['certificate_checks']}"
    paragraph("# 双容液位模型边界与失配稳健性探索")
    paragraph("## 核心增量")
    paragraph("在标称模型上，M3 相对 M2 延长了同一份方向证书可用于校正的时间。两者共用同拍、同方向、同等级和同一上游搜索。表中正值表示在同一条轨迹、同一 512 拍窗口内，前一方法的累计平方误差更低。区间按轨迹配对求双侧 95% t 区间，各档为描述性比较。每组只有两条的失稳压力点及其负向对照仅给点值。")
    body=[]
    for g in GROUPS[1:]:
        p=contrast("quantization","continuous",g);q=contrast("quantization","continuous",g,"M3","M1")
        body.append((NAMES[g],p["n"],ci(p,"gain"),ci(p,"steps"),ci(q,"gain")))
    table(["标称工况","轨迹数","M3−M2 实际降损 / cm²","M3−M2 有用拍数","M3−M1 实际降损 / cm²"],body)
    ablation=read(ROOT/"direction_ablation.json")
    assert ablation["source"]==digest(ROOT/"ablate_direction.py")
    paragraph("**增量归因。** M3 同时改变了幅值记忆与方向记忆。补充消融对同一公开前缀沿 M2 实际选中的方向保留逐起点区间；旧半空间正支撑消失后，沿伴随递推继续保留最后方向。每次 M2 换向时绑定新方向。单方向版本和完整 M3 共用上游证书、限幅与发布保底。这个顺序分解可以逐轨迹相加，结果依赖所选的单方向对照。")
    abody=[]
    for g in GROUPS[1:]:
        rs=[r for r in ablation["rows"] if r["group"]==g]
        assert len(rs)==12
        for m,j,label in [("single","M2","单方向幅值区间−M2"),("M3","single","历史方向择优−单方向"),("M3","M2","合计 M3−M2")]:
            diffs=lambda k:[r["metrics"][m][k]-r["metrics"][j][k] for r in rs]
            a,lo,hi=interval(diffs("actual"))
            abody.append((NAMES[g],label,f"{a:.4f} [{lo:.4f}, {hi:.4f}]",number(st.mean(diffs("conditional"))),number(st.mean(diffs("useful")),2)))
    table(["工况","依次加入的处理","配对实际降损 [95%]","配对离线改善","有用拍增量"],abody)
    action_differences=sum(r["other_direction_steps"] for r in ablation["rows"])
    paragraph(f"在这 {len(ablation['rows'])} 条强偏置轨迹的 {len(ablation['rows'])*512:,} 个评分拍，单方向版本与完整 M3 有 {action_differences} 拍发布位移不同。由此可将本组实际降损与有用拍数的全部增量定位到单方向下的起点—幅值区间传播；多方向择优在这些记录上未额外改变动作。这个结果仅覆盖此次消融的两组标称记录。")
    paragraph("M1 的校准门限更早允许点补偿，标称强正、强负两组均获得较大的实际降损。M3 的论文贡献可落在固定幅值区间记忆相对旧传播的增益，以及正确模型和覆盖事件上的条件风险约束。下面的失配结果限定了这两项主张可以外推的范围。")
    paragraph("## 对象、时序和计量口径")
    paragraph("A=[[0.94,0.08],[0.03,0.91]]，B=[[0.06,0.01],[0.02,0.05]]，C=[1,0]，Q=0.0025I，R=0.02，P₀=0.25I，m₀=0，W=I，Z=2。控制和中心重构沿用冻结的双泵指令及中心抖动。传感器先用干净量测与已共享中心抽取事件，发送拍才加入持续偏置。所有部署方法读取同一份公共记录。发布动作只改变输出。")
    reg=read(ROOT/"registration_v1.json")
    gates=reg["frozen_point_gates"]
    paragraph(f"起点 k=50，强偏置 ±0.35 cm，绝对查询拍为 127、255、383、511，64 节点预算，覆盖预算 0.001，L1 动作上限 1。h0={gates['h0']}，q95={gates['q95']}，M1={gates['M1']}。查询时仅得分严格大于门限才出手。独立物理、触发、中心抖动子流由 SeedSequence([202611252822, 原组号, 轨迹编号]).spawn(3) 给出。健康、强正、强负组号依次为 4、0、1。常规各取编号 0–11。跨档复用外生噪声，事件与中心可随接收反馈发生分叉。本轮探索没有增加原确认集的独立样本数。")
    paragraph("实际降损 G 为窗口 [50,561] 两项真实状态损失之差。条件改善 C 为同一窗口内逐拍 2δᵀWa−aᵀWa 的和，a 取实际 binary64 发布位移。误动作频率按健康轨迹全 608 拍至少一次非零位移计。有用拍数及期末存活按发布下界 ≥0.000625 cm² 计，M1/h0/q95 无证书，仅计非零位移。失配时达到标称门槛的拍数仍可观测，实际风险需另审。风险检查的主分母为全 608 拍内有正发布下界的动作数，容差 1e−10；0/0 表示无动作可审。单一档健康组 0/12 的双侧 95% 精确二项上限约为 26.46%。同一轨迹的各拍相关，违约拍率不能当作独立轨迹的失效概率。")
    paragraph("## 1　有限位宽")
    paragraph("发送时将载荷裁至 [−5,5] cm，在包含两端的 2ᴮ 个等距电平上取最近码，步长 10/(2ᴮ−1)，平局按偶数码。传感端和接收端用量化后的历史推进共同中心。指标 1A 的实际降损直接与模拟的物理状态比较。指标 1B 的真值滤波器在同一事件和中心历史下额外取得量化前连续载荷，是比接收端更丰富的信息集；其均值给出连续参考代理审计。以量化信息为条件的精确风险需要逐胞元积分。")
    body=[]
    for c in CASES["quantization"]:
        for g in GROUPS[1:]:
            p=contrast("quantization",c,g);r=row("quantization",c,g)
            body.append((c,NAMES[g],ci(p,"gain"),number(p["gain_change_vs_nominal"]),number(p["steps"],2),
                         f"{r['endpoint_count']}/{r['n']}",number(r['conditional_gain_mean']),fraction(r)))
    table(["位宽","强偏置","1A M3−M2 降损 [95%]","相比连续档的增量变化","有用拍数差","M3 期末存活","1B M3 代理改善","M3 代理违约/检查"],body)
    paragraph("**固定发送前缀诊断。** 对原始 36 条记录保持物理状态、事件和中心逐拍相同，仅改变接收载荷。冻结的 VectorRecord.append 要求 |中心−接收端先验预测量测|≤0.011628232298833967 cm。量化使下一拍接收端预测移动；原发送中心可能因此落在合法区间以外。触发仍然干净，固定前缀却可能不再满足冻结算法的输入合同。下表报告各组完整走完 608 拍的轨迹数，以及这些成功者中 M3−M2 的平均实际降损。失败行保留拒绝时刻与偏移量，整轨损失和风险指标记为缺失。成功者是选择后的子集。")
    diag=prefix_diagnostic(groups)
    body=[]
    for c in CASES["quantization"][1:]:
        cells=[[r for r in diag if r["scenario"]==c and r["group"]==g] for g in GROUPS]
        valid=[[r for r in cell if r["completed"]] for cell in cells]
        body.append((c,*[f"{len(v)}/12" for v in valid],*[number(st.mean(r["M3_minus_M2_gain"] for r in v)) if v else "—" for v in valid[1:]]))
    table(["位宽","健康可执行","强正可执行","强负可执行","强正成功者增量","强负成功者增量"],body)
    good=sum(r["completed"] for r in diag)
    paragraph(f"固定前缀在 {len(diag)} 个工况×轨迹回放中仅 {good} 个走完；12 bit 健康和强正各一条，强负零条，其他位宽各组均为零条。存活者不能支持跨位宽总体降损比较。位宽曲线的结论适用于收发双方基于量化后公开记录同步推进中心的运行合同。")
    paragraph("12、10 bit 的两种偏置均保留标称续航优势，本批无代理违约。没有预设等效容差，故仅报告配对变化。8 bit 起强负收益下降，6 bit 下仍有正增量。4 bit 首次在所扫位宽中出现代理违约，强正 75/2409、强负 149/1447；健康组 M1 有动作 12/12、M3 有动作 3/12。即使窗口总改善仍为正，也可能有单拍下界过高。")
    paragraph("![量化位宽、实际降损增量、有用拍数和连续参考违约比例](figures/fig_quantization.png)")
    paragraph("## 2　有界漂移")
    paragraph("对于已知确定偏置日程，发送时可由公开连续载荷恢复干净观测，静默给出以 cₜ 为中心、测量噪声 R+1/Z 的等效观测。固定了干净观测后的触发因子与状态无关，因此条件后验仍是高斯。两滤波器的增益相同，作差得到 δₜ=Fₜδₜ₋₁+γₜKₜbₜ，Fₜ=(I−KₜC)A。直接滤波与这条递推在全部 72 条衰减记录、43,776 个拍次上用有理运算逐拍核对；另以真实发布向量逐拍复算增益和违约计数。")
    paragraph("对数值合同需区分两层。旧批次以生成 binary64 数的十进制回读值及精确有理系数计算名义与真参数滤波器之差，阈值比较使用有理数。计算过程在此回读模型内精确。物理模拟、监视器和发布为 binary64。因而“精确”适用于所述观测合同的解析递推和有理阈值比较；真实状态降损及表中均值是数值统计。补充稳定扫描直接以 binary64 值的精确分数计算观测和已发布监视器到真值均值的差。")
    paragraph("令 wₛ=γₛ dᵀWΦₜ,ₛKₛ。若锚点 τ 的区间确实外包 bτ，偏置漂移对支撑的影响满足 |Σwₛ(bₛ−bτ)|≤ρΣ|s−τ|·|wₛ|。这是对每个 bₛ−bτ 单独放宽后得到的上界。相邻增量受共同约束时可以更紧。例如 τ=0 且 w₁=1、w₂=−1，原残差为 b₁−b₂，幅值最多 ρ，而逐项界为 3ρ。精确计算这个上界与证明它是所有 Lipschitz 路径的紧上界是两件事。")
    paragraph("实现中按起点从静态支撑减去上述界，并与已审计的 M2 动作比较。W=I 时，方向按 Fₜ⁻ᵀ 推进并归一化，旧脉冲的方向投影只需除以同一归一化因子。独立审计改用各脉冲直接前推后与方向相乘，并重算发布量。多次获证时原型把恒定模型相交区间作为最近证书时刻的锚；先前时刻的区间并未按漂移映射到新锚，所以上游覆盖和锚区间覆盖均未获变幅定理。若 ρ 增大，固定证据、固定记录上的各方向支撑只能降低；L1 限幅、离散方向择优、门槛与旧动作保底会造成平台和跳变。M2 为保底参照，ρ→∞ 实际能否退回 M2 还取决于漂移项是否严格为正。")
    body=[]
    for c in CASES["drift"][:6]:
        p=contrast("drift",c,"strong_positive");q=contrast("drift",c,"strong_positive","M3_rho","M3")
        a=row("drift",c,"strong_positive");b=row("drift",c,"strong_positive","M3_rho")
        body.append((c[-2:]+"%",a['rho'],ci(p,"gain"),ci(q,"gain"),f"{a['useful_steps_mean']:.1f} / {b['useful_steps_mean']:.1f}",
                     f"{fraction(a)} · {fraction(b)}",f"{a['drift_window_violations']}/{a['drift_window_checks']} · {b['drift_window_violations']}/{b['drift_window_checks']}",
                     f"{a['negative_conditional_steps']} / {b['negative_conditional_steps']}"))
    table(["总衰减","ρ / (cm/拍)","M3−M2 降损 [95%]","M3-ρ−M3 降损 [95%]","有效拍 M3 / M3-ρ","608 拍违约/检查（两法）","512 拍窗内违约/检查（两法）","窗内负改善拍（两法）"],body)
    paragraph("ρ=0 时两法重合。0–35% 的已测衰减档未见 M3 容差违约；50% 是第一个出现违约的测试档，不能据此插值得到通用安全半径。50% 时，主评分窗内静态 M3 的单拍条件改善全部非负，但有 28/1202 次低于承诺下界，全 608 拍累计 90/1478 次，集中在 2/12 条轨迹。扣除漂移余量后，同一评分窗内为 0/1202，全程为 0/1440，有用拍数由 18.1 降至 16.5。扣减改变了支撑、发布动作及宣称的下界。50% 档中代价为平均少 1.6 个有用拍，实际降损变化 −0.0083 cm²，配对区间跨零。增强方向从 +0.35 cm 出发按题设裁剪后恒为 +0.35 cm；其 60 条引用只列 M0–M3 和门限支路。2B 只比较衰减。")
    paragraph("![慢漂移的配对增量、续航和下界违约](figures/fig_drift_phase.png)")
    paragraph("## 3　动力学参数")
    paragraph("给定 Aₚ 时，真值滤波器按 Aₚ、Q 推进自己的均值与协方差，发送拍读取去除真偏置的载荷，静默拍读取同一公开中心。设 εₜ⁺ 表示标称监视器减去真实滤波器的后验均值，则下拍先验差为 Aₙεₜ⁺+(Aₙ−Aₚ)μₜ⁺。即使没有载荷攻击也存在模型误差项。更新时还会出现两套 Kalman 增益之差乘创新。误差方向可能与载荷偏置污染相抵或相加，直接以 bH 代替总污染会漏项。原发布下界以标称模型认证，失配条件改善使用真实模型审计。")
    paragraph("线性缩放 Aₚ=(1+ε)Aₙ 在 +5% 时谱半径 1.02504649，违反稳定对象前提。保留为失稳压力案例。为完整考察稳定对象，另用 Aₚ=I+(Aₙ−I)/(1+ε) 表示双容内部水力弛豫时间的标定偏差，泵指令增益保持冻结值。该定义作用于每拍内部液位增量，各特征值变为 1+(λᵢ−1)/(1+ε)。七档均验证谱半径小于 1。两套 ε 表示不同物理量，分别作配对比较。")
    for exp,title in (("stable_model","水力时间常数，在稳定域内完整扫描"),("model_mismatch","整矩阵缩放，含失稳压力点")):
        paragraph("### "+title)
        body=[]
        for c in CASES[exp]:
            h=row(exp,c,"health");m1=row(exp,c,"health","M1")
            pos=row(exp,c,"strong_positive");neg=row(exp,c,"strong_negative")
            body.append((c.split("_")[1],number(h["spectral_radius"],6),h["n"],
                        f"{m1['any_action_count']}/{h['n']} · {h['any_action_count']}/{h['n']}",
                        f"{number(m1['conditional_gain_mean'])} / {number(h['conditional_gain_mean'])}",
                        ci(contrast(exp,c,"strong_positive"),"gain"),ci(contrast(exp,c,"strong_negative"),"gain"),
                        f"{fraction(pos)} · {fraction(neg)}"))
        table(["ε","谱半径","每组 n","健康有动作 M1 · M3","健康条件改善 M1 / M3","强正 M3−M2 降损 [95%]","强负 M3−M2 降损 [95%]","强正 · 强负 M3 违约/检查"],body)
    paragraph("整矩阵缩放 +1% 时，强正组 M3 相对 M2 仍有平均降损增量，但 M3 的标称发布下界已出现 1628/2956 次违约。+2% 时对象仍稳定，强正组的增量转负，强负组仍为正；健康组 M1 在 7/12 条上误动并恶化平均条件风险，M2/M3 都未出手。向负方向扫，−1% 健康组 M1 有 1/12 次轨迹误动，−2% 又为零；数据不支持单调阈值。失稳 +5% 极端档健康组 M1、M3 均出手且平均条件风险均恶化，每组 n=2。")
    pos=[contrast("stable_model",c,"strong_positive")["gain"] for c in CASES["stable_model"]]
    neg=[contrast("stable_model",c,"strong_negative")["gain"] for c in CASES["stable_model"]]
    bad=sum(row("stable_model",c,g)["risk_violations"]>0 for c in CASES["stable_model"] if c!="tau_+0%" for g in GROUPS[1:])
    paragraph(f"在稳定水力时间常数扫描中，强正 M3−M2 的各档均值范围为 {min(pos):.4f} 至 {max(pos):.4f} cm²，强负为 {min(neg):.4f} 至 {max(neg):.4f} cm²。在非零摄动的 12 个符号×档位组合中，{bad} 个组合出现标称下界违约。收益能延续与下界仍然可靠需分别判定。")
    paragraph("![稳定摄动与整矩阵缩放的配对收益和健康误动](figures/fig_model_mismatch.png)")
    paragraph("## 逐方法数据表")
    paragraph("每行分母为该工况全部轨迹。G、C 是 512 拍累计量的组内均值，负 C 轨迹按窗口累计 C<0 计，负 C 拍按单拍 C<0 计。旧版原始 JSON 中的 loss 字段存了降损的相反数，本报告只取约定的 actual_gain 和独立复算的配对差。出手为全程出现非零动作的轨迹数。仅在健康工况称为误动。有用与期末对点方法按活动动作计，对证书方法按发布下界计。全部方法对照和相对连续/零失配档的配对增量变化分别见 trajectory_metrics.csv 和 incremental_comparisons.csv。")
    for exp,title in (("quantization","量化（中心反馈）"),("drift","漂移"),("stable_model","稳定水力参数"),("model_mismatch","整矩阵缩放")):
        paragraph("### "+title)
        table(["场景","组","方法","n","G","C","负 C 轨迹","负 C 拍","平均有用拍","期末/总数","出手/总数","下界违约/正界检查"],[
            (r["scenario"],NAMES[r["group"]],r["method"],r["n"],number(r["actual_gain_mean"]),number(r["conditional_gain_mean"]),
             r["negative_conditional_trajectories"],r["negative_conditional_steps"],number(r["useful_steps_mean"],1),f"{r['endpoint_count']}/{r['n']}",
             f"{r['any_action_count']}/{r['n']}",fraction(r) if r["certificate_checks"] is not None else "—")
            for r in sums if r["experiment"]==exp])
    paragraph("## 算力、版本与复核")
    table(["归档批次","实际计时记录（去别名）","有效计算核时"],[(k,n,number(h,4)) for k,(n,h) in cost.items()])
    prefix_hours=sum(r["cpu_seconds"] for r in diag)/3600
    hours=sum(v[1] for v in cost.values())
    extra=0
    for folder in ["data_v1/drift","data_v2_attempt/model_mismatch","stable_preflight/stable_data"]:
        extra+=sum(read(p)["cpu_seconds"] for p in (ROOT/folder).glob("*.json"))/3600
    extra+=sum(read(p)["cpu_seconds"] for p in (ROOT/"prefix_preflight/prefix_data").glob("*.json"))/3600
    extra+=sum(read(p)["cpu_seconds"] for p in (ROOT/"data_v3/model_mismatch").glob("eps_p5*"))/3600
    audit_hours=sum(r["cpu_seconds"] for r in read(ROOT/"drift_oracle_audit.json"))/3600
    ablation_hours=sum(r["cpu_seconds"] for r in ablation["rows"])/3600
    sample_hours=sum(r["cpu_seconds"] for rs in read(ROOT/"replay_samples.json").values() for r in rs)/3600
    paragraph(f"纳入的成功计算共 {hours:.4f} 核时，含稳定扫描中单独核对的三条零档轨迹。已保存的排错、替换版本及未纳入记录另有 {extra:.4f} 核时。固定前缀诊断 {prefix_hours:.4f} 核时，独立漂移逐拍复核 {audit_hours:.4f} 核时，四版本抽样重放 {sample_hours:.4f} 核时，单方向消融 {ablation_hours:.4f} 核时。以上有记录的用量小计 {hours+extra+audit_hours+sample_hours+ablation_hours+prefix_hours:.4f} 核时。中断的工作进程、重复运行、未落盘先导及重建耗时缺少完整计量，全项目实际总用量只能给出下界。每条成功轨迹取自身 CPU 计时；恢复日志里重复读取旧轨迹的计时不重复累加。")
    logs=read(ROOT/"run_log_v3.json")
    longest=max(logs,key=lambda r:r["wall_seconds"])
    paragraph(f"原整矩阵缩放批次按 6 条分批保留 64 节点。最慢的已记录 6 条批次为 {longest['scenario']} / {longest['group']} / {longest['index_start']}–{longest['index_stop']-1}，墙钟 {longest['wall_seconds']/60:.2f} 分钟，超过 25 分钟。+5% 第一版 Decimal 指数溢出，重跑时扩展指数范围；极端 ±5% 缩样后每组 2 条。标准档、稳定扫与非零衰减均各组 12 条。可选正弦未运行。")
    paragraph("四个历史计算器按各自登记 Git 提交获取。source_layout.json 指定还原登记时混合换行所需的行号，恢复后对原始字节验证登记 SHA-256。抽样重放逐条匹配公开前缀 SHA-256、整数计数及实数指标（绝对容差 1e−10，相对容差 1e−12）。登记表没有回填。稳定扫另外绑定源码和种子，零摄动时独立核对三条轨迹。完整重算和仅重建统计的命令见 README.md。")
    return "\n".join(text).rstrip()+"\n"


def main():
    groups,cost=load_rows()
    for v in range(1,5):source(v)
    summary,detail,pairs=stats(groups)
    for name,families in (("quantization",{"quantization"}),("drift",{"drift"}),("model_mismatch",{"model_mismatch","stable_model"})):
        write_csv(name+"_summary.csv",[r for r in summary if r["experiment"] in families])
    write_csv("trajectory_metrics.csv",detail)
    write_csv("incremental_comparisons.csv",pairs)
    plots(summary,pairs)
    (ROOT/"robustness_report.md").write_text(report(groups,cost,summary,pairs),encoding="utf8",newline="\n")
    files=["robustness_report.md","quantization_summary.csv","drift_summary.csv","model_mismatch_summary.csv","trajectory_metrics.csv","incremental_comparisons.csv",
           "figures/fig_quantization.png","figures/fig_drift_phase.png","figures/fig_model_mismatch.png","drift_oracle_audit.json","direction_ablation.json","source_layout.json","stable_registration.json","prefix_registration.json","fixed_prefix_diagnostic.csv","replay_samples.json"]
    (ROOT/"report_manifest.json").write_text(json.dumps({f:digest(ROOT/f) for f in files},indent=2)+"\n",encoding="utf8",newline="\n")
    print("validated registered cells",len(groups),"trajectory/method rows",len(detail),"paired comparisons",len(pairs))


if __name__=="__main__":
    main()
