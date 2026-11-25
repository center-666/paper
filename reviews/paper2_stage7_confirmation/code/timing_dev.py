"""Measure the remaining design cells under the same four-worker configuration."""
from concurrent.futures import ProcessPoolExecutor
from run import trial,TASK,DEV_SEED,warmup
if __name__=="__main__":
    with ProcessPoolExecutor(max_workers=4,initializer=warmup) as pool:
        futures=[pool.submit(trial,g,0,DEV_SEED,{"h0":"0"},"development","design-dev-v1")
                 for g in ("weak_early","weak_late","strong_late","health")]
        for f in futures:
            f.result()
