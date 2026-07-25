# Testing a FastAPI app that lives in a subfolder (e.g. `apps/api/app/`)

When the project layout puts the API under `apps/api/app/` rather than at
the repo root, pytest needs three things to discover and run the tests
correctly. This pattern was extracted from the `competitors` project
(`/root/.hermes/projects/competitors/apps/api/tests/`).

## The three things

### 1. `apps/api/` on `sys.path` via conftest

`apps/api/tests/conftest.py` starts with:

```python
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))
```

Without this, `from app.foo import bar` fails with `ModuleNotFoundError:
No module named 'app'` when the test is run from the project root.

### 2. `tests/__init__.py` *removed* at the repo root

If both `tests/` (pipeline tests at the repo root) and
`apps/api/tests/` exist, and the repo-root `tests/` has an
`__init__.py`, pytest tries to collect both as a package. That breaks
because the repo-root `tests/` doesn't know how to import `app/`.

Delete the repo-root `tests/__init__.py` (just `touch` is enough; never
created one in the first place is also fine). Now pytest collects both
as `rootdir`-relative directories rather than as a package.

### 3. `importlib.reload()` between tests when env vars drive config

If any of `app.config`, `app.db`, `app.main`, etc. read env vars at
import time, the test fixtures need to reload those modules after each
test sets new env vars. Pattern:

```python
@pytest.fixture()
def app_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("SESSION_SECRET", "test-secret-...")
    monkeypatch.setenv("DASHBOARD_USERNAME", "operator")

    # Drop any cached `app.*` modules so the reload picks up new env.
    import importlib, sys
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    # Build a bcrypt hash for the seeded user (round 4 in tests, not 12).
    import bcrypt
    seed = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", seed)

    from app.main import app
    return app
```

The bcrypt `rounds=4` instead of 12 keeps the test suite fast (the
default 12 rounds takes ~250 ms per test).

## What NOT to do

- Don't try to use `pytest.ini` or `pyproject.toml` `testpaths` to make
  the import work — `sys.path` is the only reliable lever for a
  nested-package layout.
- Don't set `pythonpath` in `pyproject.toml` to `[".", "apps/api"]` —
  it pollutes the global namespace and shadows the repo-root
  `pipeline/` package when both are collected in the same pytest run.
- Don't `from app.main import app` at the top of `conftest.py` — the
  test fixture needs to be the only place that builds the app, so
  env-var-driven config is read once per test.

## Why this lives in the checklist skill

The `apps/api/` subfolder pattern is common in multi-project workspaces
(`/root/.hermes/projects/<project>/`). The three things look obvious in
hindsight but cost 20+ minutes to debug the first time. Codifying the
pattern means the next project that adopts the layout gets it right
on the first try.

## Worked example

The `competitors` project at
`/root/.hermes/projects/competitors/apps/api/tests/conftest.py`
implements all three. The full test suite (21 tests for the in-dashboard
auth flow + 16 tests for the API + 57 tests for the pipeline = 101
total) runs in ~2.5 seconds with this layout.