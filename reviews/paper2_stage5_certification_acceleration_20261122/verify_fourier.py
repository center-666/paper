"""Replay every accepted leaf and verify that its binary tree covers the root."""
import argparse,csv,hashlib,json
from pathlib import Path
from fractions import Fraction
from decimal import localcontext
from certify_fourier import HERE,I,D,PRECISION,gap_lower


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",required=True)
    parser.add_argument("--gap",required=True)
    parser.add_argument("--target",default=".0001")
    args=parser.parse_args()
    stem=f"{args.model}_gap{D(args.gap)}_target{D(args.target)}"
    folder=HERE/"fourier_certificates"
    meta=json.loads((folder/(stem+".json")).read_text(encoding="utf8"))
    if meta["status"]!="CERTIFIED" or meta["pending"]!=0:raise AssertionError("Unresolved domain")
    digest=hashlib.sha256((folder/(stem+".csv")).read_bytes()).hexdigest()
    assert digest==meta["leaves_sha256"]
    assert meta["source_sha256"]==hashlib.sha256((HERE/"certify_fourier.py").read_bytes()).hexdigest()
    rows=list(csv.DictReader((folder/(stem+".csv")).open(encoding="utf8")))
    root=tuple(I(D(x["lo"]),D(x["hi"])) for x in meta["root_box"])
    widths=[x.hi-x.lo for x in root]
    cache={"":root};paths=set();weight=Fraction(0);minimum=None
    def get_box(path):
        if path in cache:return cache[path]
        parent=get_box(path[:-1])
        axis=max(range(3),key=lambda i:(parent[i].hi-parent[i].lo)/widths[i])
        with localcontext() as ctx:
            ctx.prec=PRECISION
            mid=(parent[axis].lo+parent[axis].hi)/2
        box=list(parent)
        box[axis]=(I(parent[axis].lo,mid) if path[-1]=="0" else I(mid,parent[axis].hi))
        cache[path]=tuple(box)
        return cache[path]
    for index,row in enumerate(rows):
        path=row["path"]
        assert path not in paths and all(path[:i] not in paths for i in range(len(path)))
        paths.add(path);weight+=Fraction(1,2**len(path))
        box=get_box(path)
        for label,interval in zip(("S","z1","z2"),box):
            assert interval.lo==D(row[label+"_lo"]) and interval.hi==D(row[label+"_hi"])
        lower=gap_lower(box,D(args.gap),D(row["omega"]))
        assert lower==D(row["gap_lower"]) and lower>=D(args.target)
        minimum=lower if minimum is None else min(minimum,lower)
        if (index+1)%2000==0:print(stem,"verified leaves",index+1,flush=True)
    # Also test the reverse prefix relation, independent of file ordering.
    for path in paths:
        assert all(path[:i] not in paths for i in range(len(path)))
    assert weight==1 and len(rows)==meta["leaves"]
    result={"status":"PASS","model":args.model,"amplitude_gap":args.gap,
            "verified_leaves":len(rows),"minimum_gap_lower":str(minimum),
            "prefix_free_tree_kraft_sum":str(weight),"root_domain_covered":True,
            "every_leaf_interval_recomputed":True,"random_samples_generated":False,
            "certificate_sha256":hashlib.sha256((folder/(stem+".json")).read_bytes()).hexdigest()}
    (folder/(stem+"_verification.json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(result))


if __name__=="__main__":main()
