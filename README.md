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

```bash
ae-upload configure
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser and download metadata.json
ae-upload validate metadata.json
ae-upload upload ./my_data_directory         # creates draft by default
# ae-upload upload ./my_data_directory --publish  # submits for review when a community is configured
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
