# Task 1 formula package

Use the archived source snapshots and Task 0.5 records to reproduce the deterministic algebra and saved-data checks. From the repository root, run with the project's NumPy-enabled Python:

```powershell
python -B reviews/g1_communication_behavior/task1/code/task1_formula_checks.py
python -B reviews/g1_communication_behavior/task1/code/task1_formula_checks.py --verify
```

The first command writes three deterministic validation outputs beneath `validation/`; the second recomputes and compares their UTF-8 bytes. It does not run the simulator, read trajectory NPZs, invoke RNGs, calibrate thresholds, or create Seed data. It verifies archived source hashes against `environment.json` and checks the Task 0.5 artifact manifest. SHA256 values for the package are in `SHA256SUMS.txt`.

The archived Python files are evidence snapshots only. Do not execute them as an experiment.
