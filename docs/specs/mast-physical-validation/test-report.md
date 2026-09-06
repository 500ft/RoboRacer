# LiDAR Mast Physical Validation — Test Report

Status: **software input/provenance enforcement tested; physical measurement pending**.
Updated 2026-09-06. The original five tests did not establish enforcement of the
written matrix or as-built-reference requirement. This replaces that overly
broad status claim, not the historical physical protocol thresholds.

## Automated acceptance-gate checks

- rejects a 0.01 mm indicator at the planned 20 N maximum load;
- accepts a 0.001 mm indicator at the same load;
- rejects incomplete x/y matrices, insufficient/incomplete cycles, missing
  direction/load pairs, duplicate cells, invalid categories and non-finite data;
- applies axis-specific checked reference values instead of nominal constants;
- checks artifact hashes, model-source commit and a distinct physical-reference
  commit, specimen/drawing linkage, calibration IDs/date, uncertainty linkage,
  and instrument measurability; rereads artifacts before producing a verdict;
- labels passing synthetic fixtures `SIMULATED_AGREEMENT`; a missing campaign
  is `INCONCLUSIVE`; the old CLI invocation without `--campaign` exits 2;
- labels a clean synthetic disagreement `SIMULATED_DISCREPANCY`;
- returns INCONCLUSIVE for excessive U95 or hysteresis.

The physical `VALIDATED` branch is exercised only with **mocked Git provenance
over synthetic unit-test inputs**. This is a software branch test, not an
authenticated physical campaign. File/hash checks do not establish the
adequacy of FEA assumptions, metrology or uncertainty propagation.

Run:

```bash
python experiments/test_mast_physical_validation.py
```

Physical results, calibration identifiers, uncertainty components, exclusions,
and the final verdict will be appended only after the frozen protocol is run.

Evidence: [baseline reproduction](../../../evidence/sprint-2026-09-05/baseline.md),
[red matrix tests](../../../evidence/sprint-2026-09-05/red-matrix.log),
[red provenance tests](../../../evidence/sprint-2026-09-05/red-provenance.log),
[green portable suite](../../../evidence/sprint-2026-09-05/green-portable.log).
Twenty mast tests pass, as do the other four portable CI entry points.
Local Python 3.11.8 differs from CI's Python 3.10; Docker/full legacy Gym
regeneration and physical testing were not run. See the
[review index](../../REVIEW_READY.md) for current candidate/evaluation status.
