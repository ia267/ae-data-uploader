# Repo Maturity Backlog

Future improvements to bring this repository closer to a production-grade workflow.

## Priority 1: Immediate

- [ ] Enable CI on `push` and `pull_request` (not only `workflow_dispatch`)
  - File: `.github/workflows/ci.yml`
  - Goal: every PR and branch push is tested automatically.

- [ ] Add lint/type jobs in CI
  - Commands:
    - `black --check .`
    - `flake8 src tests`
    - `mypy src`
  - Goal: fail fast on formatting, style, and typing issues.

- [ ] Add branch/review governance
  - Add `CODEOWNERS`
  - Add PR template and issue templates
  - Enforce branch protections in GitHub settings
  - Goal: consistent review quality and change control.

## Priority 2: High

- [ ] Add coverage reporting and a minimum threshold
  - Example: `pytest --cov=src --cov-report=term-missing --cov-fail-under=<threshold>`
  - Goal: track and protect test coverage over time.

- [ ] Add integration tests for real upload flows
  - Focus scenarios:
    - draft creation
    - publish path
    - community submission/review path
    - `custom_fields.domain` persistence
  - Goal: catch regressions in real Invenio interactions.

- [ ] Replace placeholder project URLs in `pyproject.toml`
  - Update `Homepage` and `Issues` to real repository links.
  - Goal: correct package metadata for users and tooling.

## Priority 3: Medium

- [ ] Add release/versioning process
  - Add `CHANGELOG.md`
  - Define semantic versioning policy
  - Add release/tag workflow
  - Goal: predictable releases and upgrade notes.

- [ ] Add dependency/security automation
  - Enable Dependabot or Renovate
  - Add `pip-audit` in CI
  - Add CodeQL/security scanning
  - Goal: reduce supply-chain and vulnerability risk.

## Suggested Execution Order

1. CI triggers (`push` + `pull_request`)
2. Lint/type checks in CI
3. CODEOWNERS + PR template + branch protections
4. Coverage gate
5. Integration tests (Invenio flows)
6. Fix package URLs
7. Changelog/release automation
8. Dependency/security automation
