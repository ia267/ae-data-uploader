# Quick Start Guide

Fastest path to your first upload with `ae-upload`.

## Installation

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
python -m venv venv
source venv/bin/activate
python -m pip install -e .
```

On Debian or Ubuntu, run `sudo apt install python3-venv` first if the virtual
environment command is unavailable.

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
