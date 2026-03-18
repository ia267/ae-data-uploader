# User Docs

Detailed usage guide for `ae-upload`.
For the shortest first-run path, use `QUICKSTART.md`.

## Install

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

## Configure Credentials (one-time setup)

Run this once to save your credentials to `.env` in your current directory. After setup, you only need to run it again if your credentials or preferred community changes.

**Important:** The `.env` file is created in your current working directory. To use credentials from a different directory, use the `--env-file` option:

```bash
ae-upload upload ./data --env-file /path/to/.env
```

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
INVENIO_COMMUNITIES=ae-dept-data,future-lab-data
```

Notes:
- `CUSTOM_FIELD_NAMESPACE` is optional for most users; default is `domain`.
- Most users can leave the default upload destination alone and do not need to
  set community values manually.
- `INVENIO_COMMUNITY` is optional; default is `ae-dept-data`.
  It may be either the community UUID or the slug.
- `INVENIO_COMMUNITIES` is optional; when set, it is a comma-separated allowlist
  of approved community UUIDs/slugs for uploads.
  If it is unset, `INVENIO_COMMUNITY` is treated as the single approved target.
- ORCID is optional. If you do not have one, omit `person_or_org.identifiers`.
- You can also pass credentials on each command with `--url` and `--token`.

## Per-Dataset Workflow

For each new dataset you want to upload:

### Create Metadata

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

### Upload Data

Metadata is automatically validated during upload. You can optionally validate beforehand if needed:

```bash
ae-upload validate metadata.json
ae-upload validate metadata.json --verbose
ae-upload validate metadata.json --schema schema.json
```

Directory upload:

```bash
ae-upload upload ./my_data
```

`upload` creates a draft by default. After upload, review the draft in the Invenio UI and publish when ready.

For automated publishing via CLI (optional):

```bash
ae-upload upload ./my_data --publish
```

When using `--publish`:
- with the default configuration, the draft is submitted for review using the
  standard approved destination;
- when `INVENIO_COMMUNITIES` is set, `--community` must match one of the
  approved communities in that allowlist;
- the target community is validated before the uploader creates a draft or
  uploads files;
- without a community, the command fails unless `--force-direct-publish` is set.

Single file upload:

```bash
ae-upload upload ./my_data/file.h5 --metadata /path/to/metadata.json
```

Common options:

```bash
ae-upload upload ./my_data --publish
ae-upload upload ./my_data --community future-lab-data --publish
ae-upload upload ./my_data --no-zip
ae-upload upload ./my_data --metadata /path/to/metadata.json
ae-upload upload ./my_data --schema schema.json
ae-upload upload ./my_data --auto-index --index-pattern "*.h5"
```

## Advanced Community Targeting

Most users should skip this section.

Use this only if you need to target a non-default approved community or allow
multiple approved destinations.

- `INVENIO_COMMUNITY` sets the default approved community.
- `INVENIO_COMMUNITIES` defines the approved allowlist of communities.
- `--community <community-id-or-slug>` overrides the default for a single
  upload, but only to one of the approved communities.

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
