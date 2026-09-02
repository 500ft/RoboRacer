#!/usr/bin/env python3
"""Regression test for the njit dynamics loader.

Two defects previously blocked 11 of 15 registered figure groups from regenerating:

1. ``load_vehicle_dynamics_st(module_name=...)`` worked only for the canonical name
   ``"dynamic_models"``. The kernels in ``gym/f110_gym/envs/dynamic_models.py`` are
   ``@njit(cache=True)``, and numba resolves a cached function's defining module through
   its canonical name; the on-disk cache index records whichever name loaded the source
   file *first*, so the second alias in a process raised
   ``ModuleNotFoundError: No module named 'dynamic_models'`` during type inference.

2. ``install_numba_stub_if_missing()`` raised ``ValueError`` on a second call in one
   process, because a stub it installed earlier has ``__spec__ is None`` and
   ``importlib.util.find_spec`` rejects that.

Defect 1 was order-dependent, so it did NOT reproduce when a single generator ran alone in
a fresh interpreter with a cold cache. This test therefore loads every alias that callers
actually use **sequentially in one process**, which is the condition that exposed it.

Run: ``PYTHONPATH=gym python experiments/test_dynamics_loader.py``
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

import numpy as np

from roboracer.dynamics import (
    DEFAULT_DYNAMIC_PARAMS,
    install_numba_stub_if_missing,
    load_vehicle_dynamics_st,
)

# Every module_name passed by a caller in this repository. Keep in sync with:
#   experiments/dynamic_model_replay.py    -> "dynamic_models"
#   experiments/fit_dynamic_parameters.py  -> "sysid_dynamic_models"
#   gym/roboracer/identification.py        -> "roboracer_identification_dynamic_models"
#   load_vehicle_dynamics_st default       -> "roboracer_dynamic_models"
CALLER_MODULE_NAMES = [
    "sysid_dynamic_models",
    "roboracer_identification_dynamic_models",
    "dynamic_models",
    "roboracer_dynamic_models",
]

PARAM_ORDER = [
    "mu", "C_Sf", "C_Sr", "lf", "lr", "h", "m", "I",
    "s_min", "s_max", "sv_min", "sv_max", "v_switch", "a_max", "v_min", "v_max",
]


CHILD = r"""
import sys, pathlib, numpy as np
sys.path.insert(0, "gym")
from roboracer.dynamics import load_vehicle_dynamics_st, DEFAULT_DYNAMIC_PARAMS as P
ORDER = %r
fn = load_vehicle_dynamics_st(pathlib.Path(%r), module_name=sys.argv[1])
out = fn(np.array([0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0]),
         np.array([0.1, 0.5]), *[P[k] for k in ORDER])
print(repr([float(v) for v in out]))
"""


def _load_in_child(alias: str, cache_root: Path) -> tuple[int, str, str]:
    """Load the kernels under ``alias`` in a fresh interpreter sharing ``cache_root``."""
    import subprocess

    env = dict(os.environ)
    env["PYTHONPATH"] = str(GYM_ROOT)
    env["NUMBA_CACHE_DIR"] = str(cache_root)
    proc = subprocess.run(
        [sys.executable, "-c", CHILD % (PARAM_ORDER, str(REPO_ROOT)), alias],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=600,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def test_stub_installer_is_idempotent() -> None:
    """Repeated calls must be a no-op.

    This exercises the real defect only in an interpreter where numba is *absent* (the
    stub path); where numba is installed it is a trivial early return. Run this file in
    both a numba and a non-numba environment to cover both.
    """
    for call in range(1, 4):
        try:
            install_numba_stub_if_missing()
        except Exception as exc:  # noqa: BLE001 - the defect raised ValueError
            raise AssertionError(
                f"install_numba_stub_if_missing() raised on call {call}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc


def test_alias_pairs_survive_a_shared_persistent_cache() -> None:
    """The regression test proper: two processes, different aliases, one cache directory.

    ``@njit(cache=True)`` writes an on-disk index keyed to the defining module's name. If
    each alias produces its own cache identity, the second process reads an index written
    under the first process's name and raises ModuleNotFoundError. Runs both orderings so
    neither name is privileged.
    """
    import itertools
    import tempfile

    pairs = list(itertools.permutations(CALLER_MODULE_NAMES, 2))
    for first, second in pairs:
        with tempfile.TemporaryDirectory() as cache_root:
            root = Path(cache_root)
            rc1, out1, err1 = _load_in_child(first, root)
            assert rc1 == 0, (
                f"first load under {first!r} failed (rc={rc1}): "
                f"{err1.splitlines()[-1] if err1 else ''}"
            )
            rc2, out2, err2 = _load_in_child(second, root)
            assert rc2 == 0, (
                f"loading {second!r} after {first!r} wrote the numba cache failed "
                f"(rc={rc2}): {err2.splitlines()[-1] if err2 else ''}. The source file is "
                f"being cached under more than one module identity."
            )
            a = np.asarray(eval(out1), dtype=float)  # noqa: S307 - our own child output
            b = np.asarray(eval(out2), dtype=float)  # noqa: S307
            assert np.allclose(a, b, rtol=0.0, atol=1e-12), (
                f"{first!r} and {second!r} gave different derivatives: max |diff| "
                f"{np.max(np.abs(a - b)):.3e}"
            )


def test_all_caller_aliases_share_one_module_object() -> None:
    objects = {}
    for name in CALLER_MODULE_NAMES:
        load_vehicle_dynamics_st(REPO_ROOT, module_name=name)
        objects[name] = sys.modules.get(name)
        assert objects[name] is not None, f"{name!r} was not registered in sys.modules"
    distinct = {id(m) for m in objects.values()}
    assert len(distinct) == 1, (
        f"the aliases resolve to {len(distinct)} distinct module objects; the source must "
        f"be imported once so numba sees a single cache identity"
    )
    # And that one object must be the module the vendored environment itself imports,
    # otherwise the gym env path and the loader path compete for the same cache entry.
    packaged = importlib.import_module("f110_gym.envs.dynamic_models")
    assert objects[CALLER_MODULE_NAMES[0]] is packaged, (
        "the loader must hand back f110_gym.envs.dynamic_models, the same module "
        "gym/f110_gym/envs/base_classes.py imports"
    )


def test_derivative_is_finite_and_stable() -> None:
    state = np.array([0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0])
    control = np.array([0.1, 0.5])
    args = tuple(DEFAULT_DYNAMIC_PARAMS[k] for k in PARAM_ORDER)
    fn = load_vehicle_dynamics_st(REPO_ROOT)
    out = np.asarray(fn(state, control, *args), dtype=float)
    assert out.shape == state.shape, f"got shape {out.shape}, want {state.shape}"
    assert np.all(np.isfinite(out)), f"non-finite derivative {out}"


def main() -> int:
    for test in (
        test_stub_installer_is_idempotent,
        test_alias_pairs_survive_a_shared_persistent_cache,
        test_all_caller_aliases_share_one_module_object,
        test_derivative_is_finite_and_stable,
    ):
        test()
        print(f"  ok  {test.__name__}")
    print("Dynamics loader regression: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
