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

If no system credential store is available (common over SSH, on headless
servers and on HPC nodes), `ae-upload` does not save the token. `upload` then
asks for it each time, or you can set `INVENIO_TOKEN` for a single command.
If you accept the risk of keeping the token in a file readable only by your
account, run:

```bash
ae-upload configure --token-file
```

To remove the saved token from your computer, for example before leaving a
shared machine:

```bash
ae-upload logout
```

This does not revoke the token. Delete it in the Invenio web interface under
**Settings → Applications → Personal access tokens**
(`<invenio-url>/account/settings/applications/`).

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
# open metadata_form.html in your browser, download metadata.json
# and save it inside the data directory you will upload
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


```bash
ae-upload upload ./my_data
```

`upload` creates a draft by default and links it to the default community
`ae-dept-data`. After upload, review the draft in the Invenio UI and submit it
for community review when ready.

Single file upload:

```bash
ae-upload upload ./my_data/file.h5
```

For a single file, `metadata.json` is read from the same directory as the file
(`./my_data/metadata.json` here) unless you pass `--metadata`.

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

## Advanced Tab Completion

`ae-upload configure` offers to enable TAB completion for commands, options and
file paths in bash, zsh and fish. If you skipped it, enable it later with:

```bash
ae-upload completion --install
```

Then open a new terminal and try `ae-upload up<TAB>`. This adds one marked
line to `~/.bashrc` or `~/.zshrc` (fish uses its completions directory).
Completion only works while the `venv` with `ae-upload` is active.

To print the script instead of installing it:

```bash
ae-upload completion zsh
```

Completion is not available in Windows PowerShell or cmd; use WSL or Git Bash
instead.

## Other Commands

```bash
ae-upload info
ae-upload logout
ae-upload schema --output schema.json
ae-upload export-form --output metadata_form.html
ae-upload generate-index ./my_data --pattern "*.h5"
```

## Troubleshooting

- Validation errors: run `ae-upload validate metadata.json --verbose`
- Connection issues: re-run `ae-upload configure` and verify token permissions
- Missing metadata: ensure `metadata.json` exists in the data directory, or pass `--metadata`

For installation/testing details, see `INSTALL.md`.
