# AE Uploader

![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Python CLI for validating aeronautics dataset metadata and uploading data to InvenioRDM.

Supports:
- Fluid mechanics datasets (`fluid_dynamics`)
- Structural mechanics datasets (`structures`)

## Install

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/ia267/ae-data-uploader.git
```

If you don't have `uv` yet, install it first:

```bash
# Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If `ae-upload` is not found afterwards, run `uv tool update-shell` and open a
new terminal.

Update to the latest version with `uv tool upgrade ae-uploader`.

To work on the code itself, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick Start

**One-time setup:**
```bash
ae-upload configure
```

**For each new dataset:**
```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser, download metadata.json
# and save it inside ./my_data_directory
ae-upload upload ./my_data_directory
```

Put `metadata.json` in the same directory as the data files you upload.
`ae-upload` reads it from there automatically and does not upload it:

```text
my_data_directory/
├── metadata.json
├── run_0000.h5
└── run_0001.h5
```

If `metadata.json` is somewhere else, pass it with
`--metadata /path/to/metadata.json`.

After `ae-upload configure`, non-secret settings are saved in your user config
directory and the token is stored in the system credential store when available.
The `configure` command only needs to run once.
Metadata validation happens automatically during upload, so you can skip directly to `ae-upload upload` if metadata already exists.
After upload, review the draft in the Invenio UI and submit it for community review when ready.

For scripts or temporary credentials, pass environment variables:
```bash
INVENIO_TOKEN=... ae-upload upload ./data
```

`ae-upload configure` stores `INVENIO_COMMUNITY` as the default approved community
and can also store `INVENIO_COMMUNITIES` to expand that approved allowlist.
Most users do not need to think about communities; the default approved destination is used automatically.
Routine uploads stay as drafts so you can check the record in the Invenio UI
before submitting it for community review. Direct publish without review is disabled.

See `QUICKSTART.md` for the minimal first-run flow.

## Common Options

```bash
ae-upload upload ./my_data
ae-upload upload ./my_data --zip
ae-upload schema --output schema.json
ae-upload export-form --output metadata_form.html
ae-upload generate-index ./my_data --pattern "*.h5"
ae-upload info
ae-upload logout
```

## Documentation

- Quick start (first upload): [`QUICKSTART.md`](QUICKSTART.md)
- User docs (detailed usage, troubleshooting, and advanced community targeting): [`USER_DOCS.md`](USER_DOCS.md)
- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Installation/testing details: [`INSTALL.md`](INSTALL.md)  
- Example metadata: [`examples/`](examples)

## License

MIT. See [`LICENSE`](LICENSE).
