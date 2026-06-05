# Quick Start Guide

Fastest path to your first upload with `ae-upload`.

## Installation

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

## Step 1: Configure Credentials (one-time)

```bash
ae-upload configure
```

This saves credentials to `.env` in your current directory.
By default uploads target community `ae-dept-data` (stored as `INVENIO_COMMUNITY`).

After this step, you only need to repeat it if your credentials or preferred community changes.

**Note:** The `.env` file is created in your current working directory. To use it from a different directory, either:
- Navigate to the directory where `.env` is located, or
- Use `ae-upload upload ./data --env-file /path/to/.env`

## Step 2: Create Metadata (for each dataset)

```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser and download metadata.json
```

## Step 3: Upload Data

```bash
ae-upload upload ./your_data_directory
```

Uploads are created as drafts and linked to the default community
`ae-dept-data`. Open the draft in the Invenio UI, check the files and
metadata, then submit it for community review when ready.

Metadata validation happens automatically during upload. Place `metadata.json` in the data directory, or pass it with `--metadata /path/to/metadata.json`.

For advanced options, including custom community targeting, see `USER_DOCS.md`.
