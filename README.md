# Chris Code

Chris Code is a free, model-independent autonomous software-engineering harness.

## Core rule

**Models propose. Tools measure. Tests prove.**

No model is trusted merely because it says a task is complete.

## v0.1 foundation

This first commit intentionally contains only the skeleton:

- deterministic controller
- swappable model interface
- persistent per-job ledger
- repository-confined file access
- command runner
- universal verifier shell
- hard iteration and paid-cost limits
- fail-closed unknown actions
- foundation tests

The default model is a `MockModel`, so the foundation cannot spend API money.

## Install

Python 3.11+:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
chris-code --doctor
chris-code "Foundation smoke test"
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest
chris-code --doctor
chris-code "Foundation smoke test"
```

## Expected result

`pytest` should report 3 passing tests.

`chris-code --doctor` should detect the repository and Python project.

Running the smoke-test task creates a durable JSON job record under `.chriscode/jobs/`.

## Next build

The next milestone will add the first real autonomous action protocol and model provider while preserving the rule that the harness—not the model—owns execution and verification.
