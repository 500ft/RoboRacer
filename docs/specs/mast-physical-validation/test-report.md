# LiDAR Mast Physical Validation — Test Report

Status: **protocol and automated gate verified; physical measurement pending**.

## Automated acceptance-gate checks

- rejects a 0.01 mm indicator at the planned 20 N maximum load;
- accepts a 0.001 mm indicator at the same load;
- returns VALIDATED only when quality gates and ±15% FEA agreement pass;
- returns DISCREPANCY for a clean measurement outside the FEA band;
- returns INCONCLUSIVE for excessive U95 or hysteresis.

Run:

```bash
python experiments/test_mast_physical_validation.py
```

Physical results, calibration identifiers, uncertainty components, exclusions,
and the final verdict will be appended only after the frozen protocol is run.
