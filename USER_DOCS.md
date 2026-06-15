# User Docs

Detailed usage guide for `ae-upload`.
For the shortest first-run path, use `QUICKSTART.md`.

## Install

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
python -m venv venv
source venv/bin/activate
pip install -e .
```

On Debian or Ubuntu, run `sudo apt install python3-venv` first if needed.
Activate `venv` again before using `ae-upload` in a new terminal.

## Configure Credentials (one-time setup)

Run this once to save your upload settings. Non-secret settings are stored in
your user config directory and the access token is stored in the system
credential store when available.

This works across the supported platforms:
- Linux: XDG user config directory, with Secret Service/KWallet/GNOME Keyring
  when available.
- macOS: user config directory, with Keychain via the system credential store.
- Windows: user config directory, with Windows Credential Manager via the
  system credential store.

If no system credential store is available, `ae-upload` saves the token in a
protected credentials file in the same user config directory.

Interactive setup:

```bash
ae-upload configure
```

Environment variables for scripts or temporary credentials:

```bash
INVENIO_URL=https://your-invenio-instance.org \
INVENIO_TOKEN=your_access_token \
ae-upload upload ./data
```

Notes:
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

`upload` creates a draft by default and links it to the default community
`ae-dept-data`. After upload, review the draft in the Invenio UI and submit it
for community review when ready.

Single file upload:

```bash
ae-upload upload ./my_data/file.h5 --metadata /path/to/metadata.json
```

Common options:

```bash
ae-upload upload ./my_data
ae-upload upload ./my_data --zip
ae-upload upload ./my_data --metadata /path/to/metadata.json
ae-upload upload ./my_data --schema schema.json
ae-upload upload ./my_data --auto-index --index-pattern "*.h5"
```

## Advanced Immediate Review Submission

Most uploads should not use this. Create the draft, check the files and
metadata in the UI, then submit it for review from there.

If the record has already been checked and should be submitted to community
review immediately after upload:

```bash
ae-upload upload ./my_data --submit-review
```

When using `--submit-review`:
- with the default configuration, the draft is submitted for review using
  `ae-dept-data`;
- when `INVENIO_COMMUNITIES` is set, `--community` must match one of the
  approved communities in that allowlist;
- the target community is validated before the uploader creates a draft or
  uploads files;
- without a community, the command fails;
- direct publish without review is disabled.

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
