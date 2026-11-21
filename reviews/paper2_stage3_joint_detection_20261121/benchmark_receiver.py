"""CPU/wall-time microbenchmark on deterministic receiver inputs, no sampling."""
import json
from pathlib import Path
import platform
import time
import numpy as np
from receiver_detector import JointReceiverDetector

HERE=Path(__file__).resolve().parent


def main():
    p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    output={"performance_random_samples_generated":False,
            "benchmark_kind":"software-only deterministic microbenchmark",
            "hardware_deadline_guarantee":False,"platform":platform.platform(),
            "repetitions":5,"updates_per_repetition":2000,
            "other_experiments_may_be_running":True,"rows":[]}
    for model in p["models"]:
        cpu=[];wall=[]
        for _ in range(output["repetitions"]):
            det=JointReceiverDetector(model["A"],model["R"],model["Z"])
            P=model["P0"]
            start=time.perf_counter();start_cpu=time.process_time()
            for t in range(output["updates_per_repetition"]):
                sent=t%5 in (0,3)
                r=model["delta"]*np.sin(t*.37)
                u=.23*np.cos(t*.13)+.11 if sent else None
                det.observe(sent=sent,innovation=u,prediction_variance=P,center_offset=r)
                Ri=model["R"]+(0. if sent else 1/model["Z"])
                P=model["A"]**2*P*Ri/(P+Ri)+model["Q"]
            cpu.append((time.process_time()-start_cpu)/output["updates_per_repetition"])
            wall.append((time.perf_counter()-start)/output["updates_per_repetition"])
        arrays_bytes=sum(x.nbytes for x in (det.b,det.d,det.log_pi,det.log_mass))
        output["rows"].append({
            "model":model["id"],"candidates":len(det.b),
            "cpu_seconds_per_update":cpu,"wall_seconds_per_update":wall,
            "median_cpu_microseconds":float(np.median(cpu)*1e6),
            "median_wall_microseconds":float(np.median(wall)*1e6),
            "persistent_numeric_array_bytes":arrays_bytes,
            "memory_note":"Only four persistent NumPy arrays; excludes Python objects, temporaries and estimator state.",
            "timing_note":"Includes validation and scalar covariance/fixture loop. Wall times under concurrent load are descriptive, not real-time guarantees."})
    (HERE/"receiver_benchmark.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(output,indent=2))


if __name__=="__main__":
    main()
