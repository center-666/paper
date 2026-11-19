"""Recompute the review comparisons from stored population results; no simulation."""
from pathlib import Path
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent


def calculate():
    source = HERE / 'vector_data/results.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    out = {}
    for name, case in data['cases'].items():
        peak = case['constants']['C_peak'] * .1 ** 2
        population = case['budget_base_row']['population_certificate']
        cb = case['constants']['C_record']
        sampling = case['sampling']
        margin = (peak - population) / cb
        assert margin > 0
        out[name] = dict(
            peak_only_bound=peak,
            population_certificate=population,
            known_reference_center=sampling['centered_known_bound'],
            two_sample_center=sampling['centered_two_bound'],
            known_center_gain_percent=100 * (1 - min(peak, sampling['centered_known_bound']) / peak),
            two_center_gain_percent=100 * (1 - min(peak, sampling['centered_two_bound']) / peak),
            known_center_strict_crossover=math.floor(math.log(20) / (2 * margin ** 2)) + 1,
            two_center_strict_crossover_per_group=math.floor(math.log(20) / margin ** 2) + 1,
            linear_segment_upper_lower_ratio=cb * case['constants']['C_pm'] / case['constants']['L_v'],
        )
        # Check the defining inequalities, including integer minimality.
        for denominator, key in [(2, 'known_center_strict_crossover'),
                                 (1, 'two_center_strict_crossover_per_group')]:
            count = out[name][key]
            assert population + cb * math.sqrt(math.log(20) / (denominator * count)) < peak
            assert population + cb * math.sqrt(math.log(20) / (denominator * (count - 1))) >= peak
        known = population + cb * math.sqrt(math.log(20) / 20000)
        two = population + cb * math.sqrt(math.log(20) / 10000)
        assert math.isclose(known, out[name]['known_reference_center'], rel_tol=1e-13)
        assert math.isclose(two, out[name]['two_sample_center'], rel_tol=1e-13)
    return dict(
        input_results_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        cases=out,
        notes=[
            'No new simulation; comparisons use stored population probabilities.',
            'Crossover counts refer to population-centered bounds, not success probabilities.',
            "Baseline is this paper's own uniform peak bound, not the sharpest possible no-record bound.",
        ],
    )


if __name__ == '__main__':
    result = calculate()
    target = HERE / 'review_comparison.json'
    if target.exists():
        assert result == json.loads(target.read_text(encoding='utf-8'))
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, simulated=False, cases=result['cases']), indent=2))
