# Protocol-based testability for external subsystems

When the code under test talks to a real external system (a CLI binary,
a remote API, a database, a subprocess, a hardware device), the
straightforward TDD path is: spin up the real system in tests, run
the unit, assert. That fails in three common ways:

- The system isn't available on the test runner (e.g. `opencli` not
  installed on the CI image; a dev-VPS-only binary).
- The system has side effects (writes to a real Instagram account,
  sends an email, charges a card).
- The system is non-deterministic (rate limits, network timeouts,
  cold-cache startup cost).

The fix is **dependency injection via `typing.Protocol`**: declare a
minimal Python Protocol that the production code uses, and pass the
real implementation in production, a deterministic fake in unit tests.
Integration tests against the real subsystem are a separate, thin
target — and they're the only place the real wire format is verified.

This file is the worked pattern, with the gotchas that fall out of it.

## The pattern in five lines

```python
from typing import Protocol

class WhisperPort(Protocol):
    def transcribe(self, audio_path: Path, **kwargs: Any) -> TranscriptionResult: ...

def collect_for_account(*, whisper: WhisperPort, ...) -> CollectResult:
    result = whisper.transcribe(audio_path)
    ...
```

That's it. The collector does not import `FasterWhisperBackend`. The
real wire is wired in `cli.py`; the unit test passes a `FakeWhisper`.

## The test

```python
class _FakeWhisper:
    def transcribe(self, audio_path: Path, **kwargs: Any) -> TranscriptionResult:
        return TranscriptionResult(
            text="hello", language="en", language_probability=0.99,
            segments=[], model="tiny", device="cpu",
            compute_type="int8", duration_ms=120,
        )

def test_collector_writes_staged_batch(...):
    result = collect_for_account(..., whisper=_FakeWhisper())
    assert result.accepted_count == 1
```

Three things to notice:

- The fake satisfies the Protocol by **structural typing** — no
  `class _FakeWhisper(WhisperPort):` line, no base class. That's the
  point. If the Protocol changes, mypy/pyright catches the missing
  method on the fake at type-check time. If the fake has more methods
  than the Protocol needs, that's fine.
- The test never imports `faster_whisper`. The CI image never installs
  it. The whole module of the real subsystem is irrelevant.
- The fake can simulate failures by raising:

  ```python
  class _FakeWhisperBroken:
      def transcribe(self, audio_path, **kwargs):
          raise RuntimeError("model file not found")
  ```

  and the production code's exception handling is testable too.

## When to define the Protocol

Define the Protocol **at the same time you write the test that needs
the fake**. Not before, not after. The Protocol is a *response* to the
test's demand for a fake, not a design artifact you sketch up front.

Practical sequence in RED-GREEN-REFACTOR:

1. **RED**: write the integration test (the one that would import
   `faster_whisper.WhisperModel`). Watch it fail with
   `ModuleNotFoundError` or `ImportError` — this proves the
   test would have triggered the slow path.
2. **REFACTOR the test**: instead of importing the real class, define
   a Protocol in the production module, type the parameter as
   `WhisperPort`, and pass a fake in the test. Watch the test STILL
   fail — for the right reason (production code is not yet written).
3. **GREEN**: implement the production code. Wire the real backend
   in `cli.py`.
4. **Integration test** (separate target): a single slow test that
   runs the real backend against a fixture, proving the Protocol
   contract matches reality.

## Gotcha 1: real backend accidentally called in unit tests

If the production module does `from faster_whisper import WhisperModel`
at import time, the unit test that imports the production module also
imports `faster_whisper`. The CI image needs the dep even though the
unit test never uses it.

Fix: **never import the real backend at module top-level**. Put the
import inside a factory function:

```python
def make_whisper_backend(*, model_name: str, device: str, compute_type: str) -> WhisperPort:
    from faster_whisper import WhisperModel   # late import
    return _RealWhisperAdapter(WhisperModel(model_name, device=device, compute_type=compute_type))
```

Unit tests never call `make_whisper_backend`; they pass their fake
directly. The heavy dependency stays unloaded in unit tests.

## Gotcha 2: Protocol methods that take `**kwargs`

If the production code calls `whisper.transcribe(audio_path, beam_size=5)`
but the fake's `transcribe` signature is `def transcribe(self, audio_path)`,
the test passes at runtime (Python is duck-typed) but mypy/pyright flags
it. Fix the fake to match:

```python
def transcribe(self, audio_path: Path, **kwargs: Any) -> TranscriptionResult:
    ...
```

The Protocol's signature is the source of truth; the fake just has to
declare enough parameters to be assignable.

## Gotcha 3: testing the CLI separately from the unit

The CLI module that wires the real backend (`cli.py`) is hard to unit
test if you import it. Two fixes:

- **Make the wiring a factory** that takes the adapter classes as
  parameters. The CLI parses args and calls the factory. Tests pass
  the factory a fake backend.
- **Put the wiring in a `main()` function** that the CLI entry point
  calls. Tests run the parser without running `main()`.

The first pattern is the one we used in the competitors pipeline: the
CLI has a `_WhisperAdapter` class that satisfies the Protocol. The
unit tests of the CLI import `_WhisperAdapter` to verify the wiring
shape, but never instantiate it (which would import `faster_whisper`).

## Gotcha 4: subprocess tests need `shell=False`

If the production code wraps a CLI binary, the test fake must NOT use
`shell=True`. Verify the test asserts:

```python
def fake_run(argv, *args, **kwargs):
    captured["shell"] = kwargs.get("shell", False)
    ...
    return subprocess.CompletedProcess(args=argv, ...)

monkeypatch.setattr("module.subprocess.run", fake_run)
assert captured["shell"] is False
```

The same check is in the production code:

```python
proc = subprocess.run(argv, shell=False, ...)  # explicit, not default
```

If the test ever sees `shell=True` from production, it's a security
bug AND a test gap. Catch it with the assertion above.

## Gotcha 5: subprocess env must not contain secrets

If the production code spreads secrets into the subprocess environment
(e.g. `env={"SESSION_SECRET": ...}`), the test must catch it:

```python
def fake_run(argv, *args, **kwargs):
    env = kwargs.get("env") or {}
    for k in env:
        assert "cookie" not in k.lower()
        assert "session" not in k.lower() or k == "SESSION_SECRET"
    ...
```

Subprocess env vars are observable to anyone with `ps` on the host.
Treat them as public.

## Where this pattern does NOT fit

- **Pure functions** with no external dependency — TDD them directly,
  no Protocol needed.
- **Single-use helpers** — if the code only has one caller and the
  caller is already tested, the Protocol layer is over-abstraction.
- **The one-integration-test-per-subsystem boundary** — Protocols can't
  test that the real backend actually behaves like the fake. That
  needs a thin integration test against the real system. Don't skip
  it because the unit tests are green.

## Worked example: the competitors pipeline

`pipeline/collector.py` consumes three subsystems: OpenCLI Instagram,
FFmpeg, Faster-Whisper. Each has a `*Port` Protocol in
`pipeline/collector.py`:

```python
class OpenCLIPort(Protocol):
    def session_health(self, **kwargs: Any) -> str: ...
    def fetch_user_posts(self, *, username: str, limit: int, **kwargs: Any) -> list[Any]: ...
    def download_reel(self, *, url: str, dest_dir: Path, **kwargs: Any) -> Path: ...

class MediaPort(Protocol):
    def safe_staging_dir(self, root: Path, name: str) -> Path: ...
    def validate_download(self, path: Path, **kwargs: Any) -> dict[str, Any]: ...
    def extract_audio(self, src: Path, dst: Path) -> Path: ...

class WhisperPort(Protocol):
    def transcribe(self, audio_path: Path, **kwargs: Any) -> Any: ...
```

`pipeline/cli.py` provides real adapters (`_OpenCLIAdapter`,
`_MediaAdapter`, `_WhisperAdapter`) that wire the actual
`opencli_subprocess` / `ffmpeg` / `faster_whisper` calls.

`tests/test_collector.py` defines `_FakeOpenCLI`, `_FakeMedia`,
`_FakeWhisper` and passes them in. The whole test runs in 0.02s with
zero external dependencies, but the production code path is fully
exercised.

Result: **80 tests pass in 2.7s** with no `faster_whisper`, `ffmpeg`,
or `opencli` actually invoked. The one real-faster_whisper
integration test lives outside the unit suite and runs in a separate
target against a fixture audio file.
