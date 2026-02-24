# AE Uploader

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

## Core Workflow

```bash
ae-upload configure
ae-upload generate numerical     # or: experimental
ae-upload validate metadata.json
ae-upload upload ./my_data_directory
```

## Common Options

```bash
ae-upload upload ./my_data --draft-only
ae-upload upload ./my_data --no-zip
ae-upload schema --output schema.json
ae-upload export-form --output metadata_form.html
ae-upload generate-index ./my_data --pattern "*.h5"
ae-upload info
```

## Documentation

- User guide: [`USER_DOCS.md`](USER_DOCS.md)
- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Quick start: [`QUICKSTART.md`](QUICKSTART.md)  
- Installation/testing details: [`INSTALL.md`](INSTALL.md)  
- Web form docs: [`src/ae_uploader/web/README.md`](src/ae_uploader/web/README.md)
- Example metadata: [`examples/`](examples)

## License

MIT. See [`LICENSE`](LICENSE).
