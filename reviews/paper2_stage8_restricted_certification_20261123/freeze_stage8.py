"""Freeze the strict-earlier-certificate Stage 8 replay before execution."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
STAGE7=HERE.parent/"paper2_stage7_fixed_amplitude_20261122"


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    path=HERE/"stage8_freeze.json"
    if path.exists():raise SystemExit("Stage 8 replay already frozen")
    checks=json.loads((HERE/"restricted_checks.json").read_text(encoding="utf8"))
    assert checks["status"]=="PASS"
    protocol=json.loads((HERE/"stage8_protocol.json").read_text(encoding="utf8"))
    sources=("restricted_certification.py","check_restricted.py",
             "replay_stage7_queries.py","stage8_protocol.json")
    traces={}
    for episode in protocol["selected_episodes"]:
        file=STAGE7/"results"/"fresh_confirmation"/f"b0.25_episode{episode:03d}.json"
        traces[file.name]=sha(file)
    record={"identity":"Stage 8 strict-earlier retained-domain replay",
            "base_stage7_commit":protocol["base_stage7_commit"],
            "stage7_full_search_freeze_sha256":sha(STAGE7/"fresh_confirmation_freeze.json"),
            "stage8_protocol_sha256":sha(HERE/"stage8_protocol.json"),
            "stage8_deterministic_checks_sha256":sha(HERE/"restricted_checks.json"),
            "sources":{name:sha(HERE/name) for name in sources},
            "selected_stage7_trace_hashes":traces,
            "random_samples_generated":False,
            "certificate_selection":"only successes at times strictly smaller than the target certificate time"}
    path.write_text(json.dumps(record,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
