# User Docs

Detailed usage guide for `ae-upload`.
For the shortest first-run path, use `QUICKSTART.md`.

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

Manual `.env`:

```env
INVENIO_URL=https://your-invenio-instance.org
INVENIO_TOKEN=your_access_token
CUSTOM_FIELD_NAMESPACE=domain
INVENIO_COMMUNITY=ae-dept-data
```

Notes:
- `CUSTOM_FIELD_NAMESPACE` is optional for most users; default is `domain`.
- `INVENIO_COMMUNITY` is optional; default is `ae-dept-data`.
- You can also pass credentials on each command with `--url` and `--token`.

## Create Metadata

Recommended (web form):

```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser and download metadata.json
```

Alternative (CLI template):

```bash
ae-upload generate numerical
# or
ae-upload generate experimental
```

Reference examples:
- `examples/metadata_numerical_les.json`
- `examples/metadata_experimental_piv.json`

## Validate Metadata

```bash
ae-upload validate metadata.json
ae-upload validate metadata.json --verbose
```

Use a custom schema when needed:

```bash
ae-upload validate metadata.json --schema schema.json
```

## Upload Data

Directory upload:

```bash
ae-upload upload ./my_data
```

`upload` creates a draft by default. Add `--publish` to publish immediately.

Single file upload:

```bash
ae-upload upload ./my_data/file.h5 --metadata /path/to/metadata.json
```

Common options:

```bash
ae-upload upload ./my_data --publish
ae-upload upload ./my_data --no-zip
ae-upload upload ./my_data --metadata /path/to/metadata.json
ae-upload upload ./my_data --schema schema.json
ae-upload upload ./my_data --auto-index --index-pattern "*.h5"
```

## Other Commands

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

For installation/testing details, see `INSTALL.md`.
