"""Exact rational geometry and risk checks; no fitted confidence-set claims."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json,hashlib
from projection import weighted_projection,directional_certificate,inner,interval_image
from exact_linear import matrix

HERE=Path(__file__).resolve().parent


def main():
    cases=[
        ("positive_segment",[(1,0),(3,0)]),
        ("opposite_nonzero_vectors",[(1,0),(-1,0)]),
        ("mixed_component_example",[(1,-10),(10,-1)]),
        ("triangle_positive",[(1,1),(3,1),(1,4)]),
        ("triangle_enclosing_zero",[(2,0),(-1,2),(-1,-2)]),
        ("single_vector",[(-2,1)]),
        ("signed_triangle",[(1,-1),(3,2),(-1,3)]),
    ]
    checks=[];outputs=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name)
    for Wraw in ([[1,0],[0,1]],[[1,0],[0,4]],[[2,1],[1,2]]):
        W=matrix(Wraw)
        for name,points in cases:
            result=weighted_projection(points,W)
            p=result["point"];value=result["guaranteed_gain"]
            for direction in product(range(-2,3),repeat=2):
                if direction==(0,0):continue
                d=directional_certificate(points,direction,W)
                check("directional_value_below_optimum",d["gain"]<=value)
            if value:
                optimal=directional_certificate(points,p,W)
                check("projection_direction_attains_value",optimal["point"]==p and optimal["gain"]==value)
            for candidate in product(range(-2,3),repeat=2):
                worst=min(2*inner(v,candidate,W)-inner(candidate,candidate,W) for v in points)
                check("arbitrary_action_upper_bound",
                      worst<=value-inner(tuple(candidate[i]-p[i] for i in range(2)),
                                         tuple(candidate[i]-p[i] for i in range(2)),W))
            outputs.append({"case":name,"W":Wraw,"point":[str(x) for x in p],
                            "gain":str(value),"status":result["status"]})
    component_min=(F(1),F(-10))
    W=matrix([[1,0],[0,1]])
    bad_gain=2*inner((10,-1),component_min,W)-inner(component_min,component_min,W)
    check("coordinatewise_lower_can_increase_risk",bad_gain==F(-61),str(bad_gain))
    check("vector_failure_penalty_four_is_sharp",
          (inner((1,0),(1,0),W)-(2*inner((-1,0),(1,0),W)-inner((1,0),(1,0),W)))==4)
    original=[(1,1),(2,2)]
    larger=original+[(-1,-1)]
    check("outer_set_can_force_zero",weighted_projection(larger,W)["guaranteed_gain"]==0
          and weighted_projection(original,W)["guaranteed_gain"]>0)
    points=interval_image([(1,-1),(2,1)],[(".1",".25"),(".12",".2")],include_unstarted=True)
    check("unstarted_hypothesis_prevents_positive_correction",weighted_projection(points,W)["guaranteed_gain"]==0)
    output={"status":"PASS","check_count":len(checks),"checks":checks,"examples":outputs,
            "arithmetic":"exact Fraction","performance_random_samples_generated":False,
            "input_sets_have_not_been_estimated_from_observations":True,
            "source_sha256":hashlib.sha256((HERE/"projection.py").read_bytes()).hexdigest()}
    (HERE/"projection_checks.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"examples":outputs},indent=2))


if __name__=="__main__":main()
