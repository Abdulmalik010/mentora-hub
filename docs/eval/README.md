# Evaluation

Live eval scripts (real Meta calls, real credit). Never run by pytest.

- `python -m scripts.eval_diagnosis [--mode both|parallel|single] [--reps 3]`
  compares gaps against `samples/expected.json` and writes
  `docs/eval/diagnosis.md`. Default is 2 samples x 2 modes x 3 reps = 12 runs.
- `python -m scripts.eval_matching [--limit N]` runs the 30 cases in
  `eval/matching_cases.json` (regenerate with
  `python -m scripts.make_matching_cases`) and writes `docs/eval/matching.md`.
  Full run is ~30 Wonder calls; use `--limit` for a cheap smoke first.

Both need `META_API_KEY` plus the `META_MODEL_*` ids in `.env`;
`eval_matching.py` also needs `SEED_DEMO_PASSWORD` (it seeds a fresh database).
