# Contributing

Thanks for contributing to `ae-uploader`.

## Local Setup

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
python -m venv venv
source venv/bin/activate
python -m pip install -e ".[dev]"
```

On Debian or Ubuntu, run `sudo apt install python3-venv` first if needed.

## Run Tests

```bash
python -m pytest -q
```

More detailed output:

```bash
python -m pytest -vv -ra
```

## Code Style

- Keep changes focused and minimal.
- Add/adjust tests for behavior changes.
- Prefer clear, explicit errors/messages.
- Avoid adding external network dependencies in tests.

## Pull Requests

Before opening a PR:

1. Run tests locally and ensure they pass.
2. Update docs if behavior/CLI changed.
3. Include a short PR description with:
   - What changed
   - Why it changed
   - Any migration/usage impact

Suggested PR checklist:

- [ ] Tests pass locally (`pytest`)
- [ ] New behavior is covered by tests
- [ ] Docs are updated (if needed)
- [ ] No unrelated changes included

## CI Notes

GitHub Actions workflow is present at `.github/workflows/ci.yml`.
In environments without available runners, run tests locally before merge.
