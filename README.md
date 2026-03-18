# AE Uploader

![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Python CLI for validating aeronautics dataset metadata and uploading data to InvenioRDM.

Supports:
- Fluid mechanics datasets (`fluid_dynamics`)
- Structural mechanics datasets (`structures`)

## Install

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

## Quick Start

**One-time setup:**
```bash
ae-upload configure
```

**For each new dataset:**
```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser and download metadata.json
ae-upload upload ./my_data_directory
```

After `ae-upload configure`, credentials are saved to `.env` in that directory. The `configure` command only needs to run once.
Metadata validation happens automatically during upload, so you can skip directly to `ae-upload upload` if metadata already exists.
After upload, review the draft in the Invenio UI and publish when ready.

**Note:** The `.env` file is created in your current working directory. To use credentials from a different directory:
```bash
ae-upload upload ./data --env-file /path/to/.env
```

`ae-upload configure` stores `INVENIO_COMMUNITY` as the default approved community
and can also store `INVENIO_COMMUNITIES` to expand that approved allowlist.
Most users do not need to think about communities; the default approved destination is used automatically.
`--publish` uses a safe default:
- with the default configuration, submit for review;
- without a community, fail unless `--force-direct-publish` is provided.

See `QUICKSTART.md` for the minimal first-run flow.

## Common Options

```bash
ae-upload upload ./my_data --publish
ae-upload upload ./my_data --no-zip
ae-upload schema --output schema.json
ae-upload export-form --output metadata_form.html
ae-upload generate-index ./my_data --pattern "*.h5"
ae-upload info
```

## Documentation

- Quick start (first upload): [`QUICKSTART.md`](QUICKSTART.md)
- User docs (detailed usage, troubleshooting, and advanced community targeting): [`USER_DOCS.md`](USER_DOCS.md)
- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Installation/testing details: [`INSTALL.md`](INSTALL.md)  
- Example metadata: [`examples/`](examples)

## License

MIT. See [`LICENSE`](LICENSE).
