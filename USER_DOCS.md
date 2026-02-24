# User Docs

Short guide for using `ae-uploader`.

## Install

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

## Configure Credentials

Interactive setup:

```bash
ae-upload configure
```

Or create `.env` manually:

```env
INVENIO_URL=https://your-invenio-instance.org
INVENIO_TOKEN=your_access_token
CUSTOM_FIELD_NAMESPACE=domain
```

## Typical Workflow

1. Generate metadata template:

```bash
ae-upload generate numerical
# or
ae-upload generate experimental
```

2. Edit `metadata.json` with your dataset details.

3. Validate metadata:

```bash
ae-upload validate metadata.json
```

4. Upload dataset:

```bash
ae-upload upload ./my_data
```

Useful options:

```bash
ae-upload upload ./my_data --draft-only
ae-upload upload ./my_data --no-zip
ae-upload upload ./my_data --metadata /path/to/metadata.json
```

## Useful Commands

```bash
ae-upload info
ae-upload schema --output schema.json
ae-upload export-form --output metadata_form.html
ae-upload generate-index ./my_data --pattern "*.h5"
```

## Troubleshooting

- Validation errors: run `ae-upload validate metadata.json --verbose`
- Connection issues: re-run `ae-upload configure` and verify token permissions
- Missing metadata: ensure `metadata.json` exists in the data directory, or pass `--metadata`

For full details, see `README.md`, `QUICKSTART.md`, and `INSTALL.md`.
