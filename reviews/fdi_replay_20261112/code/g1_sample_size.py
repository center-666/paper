"""Read-only planning calculation using prior seed-paired results."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'simulation/validation_runs/2026-11-11_sequential_strong_v1/per_seed_metrics.csv'
OUT=ROOT/'reviews/fdi_replay_20261112/g1_sample_size.json'


def main():
    rows=list(csv.DictReader(SOURCE.open(encoding='utf-8-sig',newline='')))
    comparisons=[]
    z_single=1.959964
    z_family=2.865
    z_power=0.841621
    for schedule in ('gap8','irregular'):
        for scenario in ('step','half_step'):
            paired=defaultdict(dict)
            for row in rows:
                if row['schedule']==schedule and row['edge_label']=='primary' and row['scenario']==scenario:
                    paired[int(row['seed'])][row['method']]=float(row['receiver_attack_mse'])
            seeds=sorted(paired)
            for baseline in ('white_window','white_cusum','white_signed_cusum'):
                differences=[paired[s]['mean']-paired[s][baseline] for s in seeds]
                mean=sum(differences)/len(differences)
                sd=math.sqrt(sum((d-mean)**2 for d in differences)/(len(differences)-1))
                baseline_mean=sum(paired[s][baseline] for s in seeds)/len(seeds)
                mde=.01*baseline_mean
                n_single=math.ceil(((z_single+z_power)*sd/mde)**2)
                n_family=math.ceil(((z_family+z_power)*sd/mde)**2)
                comparisons.append({'schedule':schedule,'scenario':scenario,'baseline':baseline,
                    'prior_independent_paired_seeds':len(seeds),
                    'baseline_receiver_attack_mse':baseline_mean,'paired_difference_sd':sd,
                    'one_percent_relative_minimum_detectable_difference':mde,
                    'prior_ci_halfwidth_as_fraction_baseline':z_single*sd/math.sqrt(len(seeds))/baseline_mean,
                    'normal_approx_n_80pct_power_single_test':n_single,
                    'normal_approx_n_80pct_power_bonferroni12_tests':n_family})
    report={'purpose':'read-only sample-size precision planning; no new trajectories or parameter selection',
      'source':SOURCE.relative_to(ROOT).as_posix(),
      'unit':'paired independent seed; not timesteps, methods, or episodes',
      'assumptions':'normal approximation, 80 percent power, two-sided alpha 0.05; familywise Bonferroni 0.05/12',
      'warning':'uses exploratory prior method variance; a future matched GLS statistic may have different variance',
      'comparisons':comparisons}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'comparisons':len(comparisons),
        'single_test_n_range':[min(x['normal_approx_n_80pct_power_single_test'] for x in comparisons),
                               max(x['normal_approx_n_80pct_power_single_test'] for x in comparisons)],
        'familywise_n_range':[min(x['normal_approx_n_80pct_power_bonferroni12_tests'] for x in comparisons),
                              max(x['normal_approx_n_80pct_power_bonferroni12_tests'] for x in comparisons)]},indent=2))


if __name__=='__main__':
    main()
