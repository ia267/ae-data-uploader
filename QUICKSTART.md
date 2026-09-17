# Quick Start Guide

Fastest path to your first upload with `ae-upload`.

## Installation

Install with [uv](https://docs.astral.sh/uv/), which puts `ae-upload` on your
PATH so it works in every terminal without activating anything:

```bash
uv tool install git+ssh://git@github.ic.ac.uk/aeronautics/ae-data-uploader.git
```

If you don't have `uv` yet, install it first:

```bash
# Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If `ae-upload` is not found afterwards, run `uv tool update-shell` and open a
new terminal. Installing needs SSH access to `github.ic.ac.uk`.

Update to the latest version with `uv tool upgrade ae-uploader`.

## Step 1: Configure Credentials (one-time)

```bash
ae-upload configure
```

This saves non-secret settings in your user config directory and stores the
token in the system credential store when available. By default uploads target
community `ae-dept-data`.

After this step, you only need to repeat it if your credentials or preferred community changes.

## Step 2: Create Metadata (for each dataset)

```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser, download metadata.json
# and save it inside the data directory you will upload
```

## Step 3: Upload Data

Put `metadata.json` in the same directory as the data files you upload.
`ae-upload` reads it from there automatically and does not upload it:

```text
your_data_directory/
├── metadata.json
├── run_0000.h5
└── run_0001.h5
```

If `metadata.json` is somewhere else, pass it with
`--metadata /path/to/metadata.json`.

```bash
ae-upload upload ./your_data_directory
```

Uploads are created as drafts and linked to the default community
`ae-dept-data`. Open the draft in the Invenio UI, check the files and
metadata, then submit it for community review when ready.

Metadata validation happens automatically during upload.

For advanced options, including custom community targeting, see `USER_DOCS.md`.
