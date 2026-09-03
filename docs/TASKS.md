# RoboRacer — tasks to completion

> **Objective.** Produce the strongest, most honestly-packaged evidence — not a completed
> project. Priority flows from leverage (does it unblock other work, or add decisive evidence)
> and from executability. Never from a calendar, and never from this project's ceiling.

Generated from an audit of the committed state of this repository. Every task is anchored to a
checked fact; no dates or estimates appear anywhere, by design.

## Two finish lines

**Ceiling.** A demonstrated third loop closure — identified model to controller to a **predicted** lap performance that a run then matches — plus a measured mast deflection against the 0.176 mm FEA prediction.

**Floor.** The two closures that already exist, packaged as a one-page case study: sysID validated on held-out track data, and an FEA prediction stated but untested, with the third named as untested.

The floor is the realistic finish line for anything gated on a measurement, and its tasks are
listed alongside the ceiling's — so the project is presentable even if the measurement never
happens.

_8 tasks · 4 Tier 0 · 5 executable now._

**Gate types.** `preregister` — write the threshold down *before* the thing it judges;
`external` — needs a resource or a person outside this repo; `build` — new work;
`hygiene` — reproducibility debt.

**Tiers.** 0 finish · 1 package · 2 park. A task whose blocker is not secured cannot be Tier 0
however decisive it is, which is why several measurements sit in Tier 2 with their
preregistration in Tier 0 ahead of them.

---

## Tier 0 — finish

### RR-01 · Apply ci-proposed/ci-gate-new-tests.patch and merge PR #3

`hygiene` · **blocked-on-workflow-scope** · after XC-02

**Why it matters.** test_dynamics_loader.py and test_replay_metrics.py are on main but nothing runs them. The numba cache-identity defect they guard is cross-process and order-dependent, so it is invisible to any single-generator run and will silently return.

**What it adds.** Turns two dormant test files into an actual regression barrier on every push.

**Done when.** ci.yml's Run evidence tests step invokes both; a branch reverting the loader fix goes red.

### RR-02 · Diagnose the nondeterministic strict item-11 regression

`build` · executable now

**Why it matters.** The Docker job failed on e456ec0 and passed on 8ea43d1 - an empty commit with the identical tree 74c99c6bf0f0d86a16872d8344ea6ca34c178e4b. That job gates releases, so it currently cannot tell a regression from noise, and the natural reading of a red check is to blame the branch.

**What it adds.** A release gate whose failures mean something.

**Done when.** Either the tolerance or the nondeterminism source is identified and committed, or the job is made deterministic; a repeated run on one tree gives one answer.

### RR-03 · Commit the predicted lap metrics from the identified model, before any controller demo

`preregister` · executable now

**Why it matters.** Two of the three loop closures exist (sysID validated on held-out track data; FEA predicting the mast mode). The third - model to controller to predicted performance to demonstration - is what makes this a closed loop rather than two separate validated models. Predicting after the demo is not a prediction.

**What it adds.** Converts the controller comparison from a benchmark into a falsifiable forecast.

**Done when.** A committed JSON of predicted lap time, RMS cross-track error and peak lateral acceleration per controller, with no demo run yet.

### RR-05 · Commit the mast deflection acceptance band before the fixture runs

`preregister` · executable now

**Why it matters.** The FEA predicts 0.176 mm. A band written after the fixture reads as fitting the criterion to the result.

**What it adds.** Makes the fixture test capable of failing.

**Done when.** Acceptance band and measurement protocol committed, no fixture data taken.

## Tier 1 — package

### RR-07 · Write the one-page model-to-control case study

`build` · executable now

**Why it matters.** The evidence is spread across a manifest, run artifacts and design docs; a reader cannot see the chain.

**What it adds.** A single readable artifact carrying the chain from identified model to controller to measured behaviour, with pending items named as pending.

**Done when.** One page committed, every number linked to its run artifact.

## Tier 2 — park

### RR-04 · Run the controller demonstration and score it against RR-03

`external` · **blocked-on-track-time** · after RR-03

**Why it matters.** Without the scored comparison the identified model is never held to account for the behaviour it predicts.

**What it adds.** The third loop closure, and the claim that the model predicts what the vehicle does.

**Done when.** Measured lap metrics committed beside the prediction, with the signed error per metric and no adjustment of RR-03.

### RR-06 · Run the mast deflection fixture and score against RR-05

`external` · **blocked-on-fixture** · after RR-05

**Why it matters.** The 0.176 mm prediction is the FEA's one falsifiable output and nothing has tested it.

**What it adds.** A measured-versus-predicted deflection, converting the modal work from analysis into validation.

**Done when.** Measured deflection committed with the pass/fail against the RR-05 band unchanged.

### RR-08 · Assemble the design package to design-review standard

`build` · executable now

**Why it matters.** The mechanical work is review-grade but not packaged as a reviewable deliverable.

**What it adds.** A package someone outside the project can evaluate without reading the repo.

**Done when.** Package committed with drawings, analysis and the verification matrix.

---

## Cross-cutting

These span repositories and are tracked identically in the others they touch.

### XC-01 · Reconcile the repo, portfolio and resume headline numbers

`hygiene` · executable now

**Why it matters.** A reviewer clicks between the three, and a disagreement there is more damaging than any single wrong number because it looks like carelessness rather than a stale file. Checked so far: the portfolio quotes 174.7 Hz (matches the repo - 163.8 Hz was the 0.20 kg placeholder tip mass, not drift) and r = 0.885 (matches), and makes no drone-mass claim. The resume was not available to check.

**Done when.** Every headline number in the portfolio and resume traced to a committed artifact, with any disagreement fixed at the source.

### XC-02 · Obtain a token with workflow scope, or route the three CI patches to a session that has one

`hygiene` · **blocked-on-workflow-scope**

**Why it matters.** Three CI barriers exist as reviewed patches and none of them run. Each guards a defect class that has already occurred once.

**Done when.** RR-01, CR-01 and ER-02 are applied and their checks appear on subsequent pull requests.

