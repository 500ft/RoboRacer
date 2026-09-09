# Proposed CI change — not active

## Review amendment — 2026-09-09

The CAD proposal is now installed as
[`.github/workflows/cad-geometry.yml`](../.github/workflows/cad-geometry.yml).
Current-session authentication was verified by the parent reviewer to include
workflow permission; the earlier token restriction below is historical, not a
current blocker. Do not reapply the CAD patch: it is retained only as the original
proposal. Hosted CAD verification is pending until the amended PR runs green.
The installed job reads version constraints directly from `cad/requirements.lock`
and accepts PRs to main or a day-1 stack base. Those constraints pin five direct
packages; they are not a platform/build/transitive dependency lock.

`ci-proposed/ci-gate-new-tests.patch` contains a workflow change that **is not installed**. Nothing in this
directory is executed by GitHub Actions; it only takes effect once someone applies it.

## Why it is a patch rather than the workflow file

The token used to open this pull request carries Contents and Pull requests scope but not
`workflow`, so it cannot write `.github/workflows/**`. That was confirmed two ways rather
than assumed:

```
git push      -> ! [remote rejected] refusing to allow a Personal Access Token to create
                 or update workflow `.github/workflows/ci.yml` without `workflow` scope
Contents API  -> 403 Resource not accessible by personal access token
```

That restriction is deliberate: it stops an automated token from silently changing what CI
runs. Shipping the change as a patch keeps that property — the diff is reviewable, and it
does nothing until a human or an authorised token installs it.

## Apply it

```bash
git apply ci-proposed/ci-gate-new-tests.patch
git add .github/workflows/ci.yml
git commit -m "ci: gate the dynamics-loader and replay-metrics tests"
```

`git apply --check ci-proposed/ci-gate-new-tests.patch` was run against this branch and succeeds.

Once applied, delete this directory — it exists only to carry the change across the
permission gap.


---

## Second proposal — `cad-geometry-workflow.patch` (RR-CAD-08)

Adds `.github/workflows/cad-geometry.yml`: installs the pinned CadQuery toolchain from
`cad/requirements.lock`, regenerates the mast geometry from `cad/roboracer/parameters.csv`, and
runs `cad/tests` (11 tests: contract, negative controls, version lock). Same reason it is a
patch: the PR token has no `workflow` scope. `git apply --check` passes.

```bash
git apply ci-proposed/cad-geometry-workflow.patch
git add .github/workflows/cad-geometry.yml && git commit -m "ci: add CAD geometry job (RR-CAD-08)"
```
