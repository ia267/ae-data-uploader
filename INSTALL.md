# AE Uploader - Installation and Testing Details

This guide is for setup and verification.  
For end-user upload workflow, use `QUICKSTART.md` and `USER_DOCS.md`.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it also installs a suitable Python if needed)
- Git
- SSH access to `github.ic.ac.uk` (for the private repository URL)

Install `uv` if you don't have it:

```bash
# Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Install

```bash
uv tool install git+ssh://git@github.ic.ac.uk/aeronautics/ae-data-uploader.git
```

`uv` installs `ae-upload` into its own isolated environment and links the
command into `~/.local/bin` (or the Windows equivalent), so there is no
virtual environment to activate.

Update, pin or remove:

```bash
uv tool upgrade ae-uploader
uv tool install --reinstall git+ssh://git@github.ic.ac.uk/aeronautics/ae-data-uploader.git@<tag-or-commit>
uv tool uninstall ae-uploader
```

### Optional libraries for index generation

`--auto-index` and `generate-index` need `h5py` for HDF5 files and `netCDF4`
for NetCDF files:

```bash
uv tool install --reinstall --with h5py --with netCDF4 git+ssh://git@github.ic.ac.uk/aeronautics/ae-data-uploader.git
```

`uv tool upgrade` keeps these extra libraries.

## Verify Installation

```bash
ae-upload --version
ae-upload info
```

If `ae-upload` is not found, run `uv tool update-shell`, open a new terminal
and try again.

## Development Setup

To change the code or run the tests, use an editable install in a virtual
environment (see also `CONTRIBUTING.md`):

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
uv venv venv
source venv/bin/activate
uv pip install -e ".[dev]"
```

While `venv` is active, `ae-upload` runs your local checkout. Outside it, the
`uv tool` install (if any) is used.

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

If `uv tool install` or `git clone` hangs or asks for a password:
- Use SSH URLs (`git+ssh://git@github.ic.ac.uk/...`), not HTTPS URLs.
- Verify SSH access: `ssh -T git@github.ic.ac.uk`
- Check loaded SSH keys: `ssh-add -l`

## Related Docs

- `QUICKSTART.md`: shortest first upload path
- `USER_DOCS.md`: detailed usage and options
- `README.md`: project overview and doc map
