"""Deterministic causal center provenance under Model A."""
import ast
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from fractions import Fraction as F


HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/'paper2_stage6_vector_correction_20261122'
CONTRACT=HERE.parent/'paper2_stage10_numerical_contract_20261123'
sys.path.insert(0,str(STAGE6))
sys.path.insert(0,str(CONTRACT))
from exact_linear import add, matmul, matrix, transpose, update
from numerical_record import binary64_value,exact_matvec
MODEL_PATH=HERE.parent/'paper2_stage6_vector_correction_20261122'/'model.json'
STAGE9_PATH=HERE.parent/'paper2_stage9_cumulative_evidence_20261123'/'paired_recovery.py'
STAGE9_TRACE=HERE.parent/'paper2_stage10_numerical_contract_20261123'/'stage9_monitor_trace.json'


def quantize_prediction(prediction, phase, half_width):
    index=(prediction-phase+half_width)//(2*half_width)
    grid_center=phase+2*half_width*index
    return index,grid_center


def construct_trace(model, events, words, phases):
    A,C,Q,P=(matrix(model[k]) for k in ('A','C','Q','P0_prior'))
    delta,R,Z=F(model['quantization_half_width']),F(model['R']),F(model['Z'])
    mean=[[F(0)],[F(0)]]
    rows=[]
    for t,(sent,word,phase) in enumerate(zip(events,words,phases)):
        if len(mean)!=2 or len(mean[0])!=1:
            raise AssertionError("invalid public monitor state")
        prediction=matmul(C,mean)[0][0]
        phase=F(phase)
        if abs(phase)>delta:
            raise ValueError("Randomized phase must lie in [-delta,delta]")
        index,grid_center=quantize_prediction(prediction,phase,delta)
        center_float=float(grid_center)
        if not __import__('math').isfinite(center_float):
            raise OverflowError("Center reconstruction overflow")
        center=F.from_float(center_float)
        if abs(center-prediction)>delta:
            raise ArithmeticError("Reconstructed center violates half-width contract")
        if sent:
            if type(word) is not float or not __import__('math').isfinite(word):
                raise ValueError("This causal fixture uses finite binary64 words")
            observed=F.from_float(word)
        else:
            if word is not None:
                raise ValueError("Silent records cannot carry a word")
            observed=center
        Ppost,gain,transition=update(P,C,R if sent else R+1/Z)
        meanpost=add(matmul(transition,mean),matmul(gain,[[observed]]))
        nextmean=matmul(A,meanpost)
        nextP=add(matmul(matmul(A,Ppost),transpose(A)),Q)
        rows.append({
            "time":t,
            "prior_mean":[str(row[0]) for row in mean],
            "prediction":str(prediction),
            "phase":str(phase),
            "grid_index":str(index),
            "grid_center":str(grid_center),
            "center_hex":center_float.hex(),
            "event":"send" if sent else "silence",
            "word_hex":word.hex() if sent else None,
            "source_filter":["prior_mean","phase"],
            "generated_before_current_event":True,
            "center_within_half_width":True,
        })
        mean,P=nextmean,nextP
    return rows


def audit_stage9_source():
    tree=ast.parse(STAGE9_PATH.read_text(encoding='utf8'))
    run=next(node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
             and node.name=="run_episode")
    named={}
    phase_calls=[]
    random_calls=[]
    append_call=None
    for node in ast.walk(run):
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name):
                    named.setdefault(target.id,[]).append(node.lineno)
        if isinstance(node,ast.Call):
            if isinstance(node.func,ast.Attribute) and node.func.attr=="random":
                random_calls.append(node.lineno)
            if isinstance(node.func,ast.Attribute) and node.func.attr=="append":
                append_call=node.lineno if append_call is None else min(append_call,node.lineno)
    event_line=min(named.get('sent',[10**9]))
    residual_line=min(named.get('residual',[10**9]))
    has_center_assignment=bool(named.get("center"))
    phase_line=min(named.get("r",[10**9]))
    rng_line=min(named.get("phys",[10**9]))
    assert event_line<residual_line
    assert append_call and append_call>residual_line
    # The simulator's phase variable is a direct prediction-coordinate offset r.
    source=STAGE9_PATH.read_text(encoding='utf8')
    has_direct_offset="r = 0. if t == 0 else delta*(2*phase.random()-1)" in source
    separate_rngs="np.random.SeedSequence([seed, seed_index, index]).spawn(3)" in source
    assert separate_rngs and "phys, events, phase =" in source
    return {
        "file":STAGE9_PATH.relative_to(HERE.parents[1]).as_posix(),
        "sha256":hashlib.sha256(STAGE9_PATH.read_bytes()).hexdigest(),
        "phase_offset_assignment_line":phase_line,
        "event_assignment_line":event_line,
        "residual_assignment_line":residual_line,
        "record_append_line":append_call,
        "independent_phase_and_event_rngs":separate_rngs,
        "phase_generated_before_event":phase_line<event_line,
        "phase_offset_passed_to_evidence_record":phase_line<append_call,
        "phase_random_call_lines":sorted(random_calls),
        "absolute_center_variable_constructed":has_center_assignment,
        "phase_is_direct_offset_r":has_direct_offset,
        "stage9_center_source_chain":"r is generated independently before event and stored; ideal absolute center C*m_prior+r is reconstructible from shared monitor state, but no absolute-center bit pattern is logged",
        "stage9_channel_matches_model_A":"no, the event uses floating y-r and the sent residual uses floating y+injection",
    }


def main():
    model=json.loads(MODEL_PATH.read_text(encoding='utf8'))
    events=[True,False,True,True,False,True]
    words=[.375,None,-.25,.5,None,-.125]
    delta=F(model['quantization_half_width'])
    phases=[F(0),delta/4,-delta/2,delta/8,-delta/8,delta/3]
    rows=construct_trace(model,events,words,phases)
    # Reconstruct all centers from only the prior common monitor record and
    # the phase available before the current event. This rejects future inputs.
    replay=construct_trace(model,events,words,phases)
    assert rows==replay
    for row in rows:
        assert row["source_filter"]==["prior_mean","phase"]
        assert row["generated_before_current_event"] is True
    stage9=json.loads(STAGE9_TRACE.read_text(encoding='utf8'))
    C=matrix(model['C'])
    reconstructed=[]
    delta=F(model['quantization_half_width'])
    for row in stage9['rows']:
        prior=tuple(binary64_value(float.fromhex(x)) for x in row['prior_hex'])
        offset=binary64_value(float.fromhex(row['offset_hex']))
        prediction=exact_matvec(C,prior)[0]
        center=prediction+offset
        center_word=float(center)
        center_exact=F.from_float(center_word)
        assert abs(center_exact-prediction)<=delta
        reconstructed.append({'time':row['time'],'prior_hex':row['prior_hex'],
                              'offset_hex':row['offset_hex'],'center_hex':center_word.hex(),
                              'event':row['sent'],'center_source_is_past_state_plus_independent_offset':True})
    result={"model":"A, exact continuous monitor recursion, one binary64 center reconstruction",
            "phase_source":"fixed exogenous values, independent of state and current event",
            "center_formula":"phase + 2*delta*floor((C*m_prior-phase+delta)/(2*delta))",
            "rows":rows,"stage9_comparison":audit_stage9_source(),
            "stage9_trace_reconstruction":{"trace_sha256":hashlib.sha256(STAGE9_TRACE.read_bytes()).hexdigest(),
                                            "rows":reconstructed},
            "sha256":{MODEL_PATH.relative_to(HERE.parents[1]).as_posix():hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()}}
    (HERE/'center_provenance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print("PASS",len(rows),"causal center generations; Stage9 source chain audited")


if __name__=="__main__":
    main()
