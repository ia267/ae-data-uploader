# AE Uploader - Installation and Testing Details

This guide is for setup and verification.  
For end-user upload workflow, use `QUICKSTART.md` and `USER_DOCS.md`.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it also installs a suitable Python if needed)
- Git

Install `uv` if you don't have it:

```bash
# Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Install

```bash
uv tool install git+https://github.com/ia267/ae-data-uploader.git
```

`uv` installs `ae-upload` into its own isolated environment and links the
command into `~/.local/bin` (or the Windows equivalent), so there is no
virtual environment to activate.

Update, pin or remove:

```bash
uv tool upgrade ae-uploader
uv tool install --reinstall git+https://github.com/ia267/ae-data-uploader.git@<tag-or-commit>
uv tool uninstall ae-uploader
```

### Optional libraries for index generation

`--auto-index` and `generate-index` need `h5py` for HDF5 files and `netCDF4`
for NetCDF files:

```bash
uv tool install --reinstall --with h5py --with netCDF4 git+https://github.com/ia267/ae-data-uploader.git
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
git clone https://github.com/ia267/ae-data-uploader.git
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

If `uv tool install` or `git clone` asks for a password, check the URL is
exactly `https://github.com/ia267/ae-data-uploader.git`. The repository is
public, so no login or SSH key is needed.

## Related Docs

- `QUICKSTART.md`: shortest first upload path
- `USER_DOCS.md`: detailed usage and options
- `README.md`: project overview and doc map
