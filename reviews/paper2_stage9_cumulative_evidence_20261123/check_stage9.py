"""Deterministic provenance and multi-interval outer-envelope checks."""
from __future__ import annotations
from dataclasses import replace
from decimal import Decimal as D
from fractions import Fraction as F
import hashlib, json, sys, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"
sys.path.insert(0,str(STAGE6));sys.path.insert(0,str(HERE))

from cumulative_envelope import EvidenceRecord, CertifiedParameterEnvelope
from vector_record import interval_fraction, I


def main():
    model=json.loads((STAGE6/"model.json").read_text(encoding="utf8"))
    checks=[]

    def check(name, condition, detail=None):
        checks.append({"name":name,"pass":bool(condition),"detail":detail})
        if not condition:raise AssertionError((name,detail))

    record=EvidenceRecord(model,epsilon=".001",amplitude_cap=".25")
    for t in range(12):
        payload=".22" if t==0 else ".00001"
        record.append(True,payload,"0")

    direction=(F(1),F(0))
    full,certificate=record.certify_full(direction,F(".15"),max_nodes=256)
    check("deterministic_fixture_full_certificate_succeeds",full["certified"],full)
    envelope=CertifiedParameterEnvelope.start(record,certificate,
        refinement_tolerance=".001",refinement_budget=256)
    second_full,second_certificate=record.certify_full(direction,F(".16"),max_nodes=256)
    check("same_time_second_full_certificate_succeeds",second_full["certified"],second_full)
    same_time_envelope=envelope
    try:
        envelope.certify_direction(record,direction,F(".15"))
    except ValueError:
        check("same_time_restricted_certificate_rejected",True)
    else:
        check("same_time_restricted_certificate_rejected",False)
    prior_components=same_time_envelope.confidence_intervals()
    same_time_envelope.apply_certificate(record,second_certificate)
    intersected_components=same_time_envelope.confidence_intervals()
    check("same_time_full_certificates_intersect_bounds",
          len(same_time_envelope.certificate_history)==2 and
          all(any(old_lo<=new_lo and new_hi<=old_hi
                  for old_lo,old_hi in prior_components[onset])
              for onset,items in intersected_components.items()
              for new_lo,new_hi in items),
          {key:[(str(a),str(b)) for a,b in value]
           for key,value in intersected_components.items()})
    confidence_components=envelope.confidence_intervals()[0]
    check("multiple_disjoint_intervals_are_retained",len(confidence_components)>=2,
          [(str(a),str(b)) for a,b in confidence_components])
    threshold=envelope._threshold(record)
    for b in (".20",".24"):
        ll=record.core.likelihood(0,I.exact(b))
        check("known_confident_point_is_retained:"+b,
              ll.lo>threshold.hi and envelope.contains_parameter(0,b),
              {"loglik_lower":str(ll.lo),"threshold_upper":str(threshold.hi)})
    check("moving_zero_not_required_to_be_retained",
          not envelope.contains_parameter(0,".22"))
    proposal=envelope.propose_direction(record)
    proposal_detail=None if proposal is None else {
        "direction":[str(x) for x in proposal["direction"]],
        "onset":proposal["onset"],
        "amplitude_interval":proposal["amplitude_interval"],
        "proposal_loglik_upper":proposal["proposal_loglik_upper"]}
    check("outer_set_generates_a_finite_direction_proposal",proposal is not None,proposal_detail)
    safe_action=envelope.directional_action(record,proposal["direction"],l1_cap=F(1))
    check("outer_set_action_has_nonnegative_proved_gain",
          F(safe_action["guaranteed_gain"])>=0,
          {"action":[str(x) for x in safe_action["action"]],
           "support":safe_action["support"],
           "gain":safe_action["guaranteed_gain"]})
    if safe_action["action"]!=(F(0),F(0)):
        direction=proposal["direction"]
        action=tuple(F(x) for x in safe_action["action"])
        support=F(safe_action["support"])
        norm=sum((action[i]*record.core.W[i][j]*action[j]
                  for i in range(2) for j in range(2)),F(0))
        denominator=sum((direction[i]*record.core.W[i][j]*direction[j]
                  for i in range(2) for j in range(2)),F(0))
        analytic_lower=2*support*sum((direction[i]*record.core.W[i][j]*action[j]
                  for i in range(2) for j in range(2)),F(0))-norm
        check("output_action_retains_minimax_risk_inequality",
              analytic_lower>=norm,{"risk_lower":str(analytic_lower),"action_norm_sq":str(norm)})
    rejected=False
    try:envelope.contains_parameter(0,.2)
    except TypeError:rejected=True
    check("binary_float_parameter_query_rejected",rejected)

    # Every stored node likelihood bound must dominate point likelihoods on
    # its interval. This checks incremental A/B/selection updates and branching.
    def check_node_upper(label):
        threshold_now=envelope._threshold(record)
        for node in envelope.nodes:
            points=(node.lower,(node.lower+node.upper)/2,node.upper)
            for point in points:
                exact=record.core.likelihood(node.onset,I.exact(point))
                check(label+"_incremental_upper_dominates_exact_point",
                      exact.lo<=node.loglik_upper,
                      {"onset":node.onset,"b":str(point),
                       "exact_lower":str(exact.lo),"stored_upper":str(node.loglik_upper)})
            check(label+"_retained_node_not_below_current_cutoff",
                  node.loglik_upper>=threshold_now.lo)

    check_node_upper("initial")

    for _ in range(2):
        record.append(True,".00001","0")
        update=envelope.advance(record,refinement_budget=64)
        check("advance_moves_to_current_prefix",envelope.time==record.time and
              envelope.observation_prefix_hash==record.prefix_hash,update)
        check_node_upper("advanced")
        for b in (".20",".24"):
            ll=record.core.likelihood(0,I.exact(b))
            cutoff=envelope._threshold(record)
            check("cumulative_outer_preserves_every_confident_point:"+b,
                  ll.lo<=cutoff.hi or envelope.contains_parameter(0,b),
                  {"loglik_lower":str(ll.lo),"threshold_upper":str(cutoff.hi),
                   "contained":envelope.contains_parameter(0,b)})

    # A later direction certificate must be strictly newer and constrain the
    # existing intervals without adding a fresh failure probability.
    full_second=record.core.certify_direction(direction,".151",epsilon=".001",
        bmax=".25",max_nodes=256)
    restricted_second,second_certificate=envelope.certify_direction(
        record,direction,F(".151"),max_nodes=256)
    check("full_and_cumulative_restricted_decisions_match",
          full_second["certified"]==restricted_second["certified"],
          {"full":full_second["reason"],"restricted":restricted_second["reason"]})
    check("later_direction_certificate_succeeds",second_certificate is not None)
    if restricted_second["certified"]:
        again_result, again = envelope.certify_direction(record,direction,F(".152"),max_nodes=256)
        check("same_wave_queries_share_prior_snapshot", again_result["certified"] and
              again.source_envelope_id==second_certificate.source_envelope_id and
              again.parent_certificate_ids==second_certificate.parent_certificate_ids)
        check("restricted_certificate_lists_only_strictly_prior_sources",
              all(record.certificates[c].time<record.time for c in second_certificate.parent_certificate_ids))
        envelope.apply_certificate(record,second_certificate)
        envelope.apply_certificate(record,again)
        check("later_certificate_bound_to_current_prefix",
              second_certificate.time==record.time and
              second_certificate.observation_prefix_hash==record.prefix_hash)
        check("later_certificate_added_to_chain",
              envelope.certificate_history[-2:]==(second_certificate,again))
        check("multiple_interval_outer_remains_nonempty",len(envelope.nodes)>0)

    # Provenance checks reject mismatched history, model, confidence budget,
    # certificate lineage, source artifacts, and binary floating endpoints.
    divergent=EvidenceRecord(model,epsilon=".001",amplitude_cap=".25")
    for t in range(12):
        divergent.append(True,".23" if t==0 else ".00001","0")
    rejected=False
    try:envelope.advance(divergent)
    except ValueError:rejected=True
    check("different_observation_prefix_rejected",rejected)

    wrong_model=dict(model);wrong_model["R"]="0.21"
    wrong_record=EvidenceRecord(wrong_model,epsilon=".001",amplitude_cap=".25")
    for t in range(12):wrong_record.append(True,".22" if t==0 else ".00001","0")
    rejected=False
    try:envelope.advance(wrong_record)
    except ValueError:rejected=True
    check("different_model_rejected",rejected)

    wrong_epsilon=EvidenceRecord(model,epsilon=".002",amplitude_cap=".25")
    for t in range(12):wrong_epsilon.append(True,".22" if t==0 else ".00001","0")
    rejected=False
    try:envelope.advance(wrong_epsilon)
    except ValueError:rejected=True
    check("different_confidence_process_rejected",rejected)

    rejected=False
    try:record.certify_full(direction,.15)
    except TypeError:rejected=True
    check("binary_float_certificate_support_rejected",rejected)

    rejected=False
    try:record.append(True,.1,0.)
    except TypeError:rejected=True
    check("binary_float_observation_rejected",rejected)

    rejected=False
    try:
        record_bad_jump=EvidenceRecord(model,epsilon=".001",amplitude_cap=".25")
        for t in range(12):record_bad_jump.append(True,".22" if t==0 else ".00001","0")
        _,bad_certificate=record_bad_jump.certify_full(direction,F(".15"),max_nodes=256)
        bad_envelope=CertifiedParameterEnvelope.start(record_bad_jump,bad_certificate,
            refinement_tolerance=".001",refinement_budget=256)
        record_bad_jump.append(True,".00001","0")
        record_bad_jump.append(True,".00001","0")
        bad_envelope.advance(record_bad_jump)
    except ValueError:rejected=True
    check("skipped_observation_updates_rejected",rejected)

    rejected=False
    try:envelope.apply_certificate(record,certificate)
    except ValueError:rejected=True
    check("same_time_or_old_certificate_rejected",rejected)

    with tempfile.TemporaryDirectory(prefix="stage9-source-") as directory:
        artifact=Path(directory)/"source.json"
        binding={"model_hash":record.model_hash,
            "confidence_process_hash":record.confidence_process_hash,
            "implementation_hash":record.implementation_hash,
            "epsilon":record.epsilon,"amplitude_cap":record.amplitude_cap,
            "observation_prefix_hash":record.prefix_hash}
        artifact.write_text(json.dumps({"source_binding":binding,
            "certificate_queries":[],"successful_certificates":[]},
            sort_keys=True),encoding="utf8")
        import hashlib
        digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
        rejected=False
        try:record.import_frozen_certificate(artifact,digest,{"time":record.time})
        except ValueError:rejected=True
        check("pinned_artifact_without_matching_query_rejected",rejected)
        query={"time":record.time,
            "direction":[str(x) for x in second_certificate.direction],
            "target_support":str(second_certificate.support),
            "level":str(second_certificate.support),"epsilon":record.epsilon,
            "amplitude_cap":record.amplitude_cap,"max_nodes":256}
        artifact.write_text(json.dumps({"source_binding":binding,
            "certificate_queries":[{"certified":True,"time":record.time,
                "direction":query["direction"],"target_support":query["target_support"],
                "level":query["level"]}],
            "successful_certificates":[{"time":record.time,
                "direction":query["direction"],"z":query["target_support"]}]},
            sort_keys=True),encoding="utf8")
        digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
        imported=record.import_frozen_certificate(artifact,digest,query)
        check("history_bound_pinned_certificate_imported",
              imported.observation_prefix_hash==record.prefix_hash and
              imported.model_hash==record.model_hash)
        rejected=False
        try:record.import_frozen_certificate(artifact,"0"*64,query)
        except ValueError:rejected=True
        check("modified_artifact_hash_rejected",rejected)
        binding["observation_prefix_hash"]="0"*64
        artifact.write_text(json.dumps({"source_binding":binding,
            "certificate_queries":[{"certified":True,"time":record.time,
                "direction":query["direction"],"target_support":query["target_support"],
                "level":query["level"]}],
            "successful_certificates":[{"time":record.time,
                "direction":query["direction"],"z":query["target_support"]}]},
            sort_keys=True),encoding="utf8")
        digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
        rejected=False
        try:record.import_frozen_certificate(artifact,digest,query)
        except ValueError:rejected=True
        check("artifact_bound_to_different_prefix_rejected",rejected)

    out={"status":"PASS","check_count":len(checks),"checks":checks,
         "multi_interval_onset0":len(confidence_components),
         "initial_outer_nodes":len(envelope.nodes),
         "certificate_count":len(envelope.certificate_history),
         "incremental_stats":envelope.stats,
         "random_samples_generated":False,
         "source_sha256":hashlib.sha256((HERE/"cumulative_envelope.py").read_bytes()).hexdigest()}
    (HERE/"stage9_checks.json").write_text(json.dumps(out,indent=2)+"\n",
        encoding="utf8",newline="\n")
    print(json.dumps({k:v for k,v in out.items() if k!="checks"},indent=2))


if __name__=="__main__":main()
