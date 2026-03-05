# AE Uploader - Installation and Testing Details

This guide is for setup and verification.  
For end-user upload workflow, use `QUICKSTART.md` and `USER_DOCS.md`.

## Prerequisites

- Python 3.9+
- Git
- SSH access to `github.ic.ac.uk` (for cloning private repository URLs)

## Install

Clone and install in editable mode:

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

Optional: install development dependencies:

```bash
pip install -e ".[dev]"
```

Alternative: install directly via SSH without cloning:

```bash
pip install git+ssh://git@github.ic.ac.uk/aeronautics/ae-data-uploader.git
```

## Verify Installation

```bash
ae-upload --version
ae-upload info
```

If `ae-upload` is not found, ensure your virtual environment is activated and reinstall with `pip install -e .`.

## Run Tests

Run the full test suite:

```bash
pytest
```

Run specific test modules:

```bash
pytest tests/test_cli.py
pytest tests/test_validate.py
```

## Install Troubleshooting

If `git clone` or `pip install` hangs:
- Use SSH URLs (`git@github.ic.ac.uk:...`), not HTTPS URLs.
- Verify SSH access: `ssh -T git@github.ic.ac.uk`
- Check loaded SSH keys: `ssh-add -l`

## Related Docs

- `QUICKSTART.md`: shortest first upload path
- `USER_DOCS.md`: detailed usage and options
- `README.md`: project overview and doc map
