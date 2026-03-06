# Quick Start Guide

Fastest path to your first upload with `ae-upload`.

## Installation

```bash
git clone git@github.ic.ac.uk:aeronautics/ae-data-uploader.git
cd ae-data-uploader
pip install -e .
```

## 1. Configure Credentials

```bash
ae-upload configure
```

This saves credentials to `.env` in your current directory.

## 2. Create `metadata.json`

```bash
ae-upload export-form --output metadata_form.html
# open metadata_form.html in your browser and download metadata.json
```

## 3. Validate Metadata

```bash
ae-upload validate metadata.json
```

## 4. Upload Data

```bash
ae-upload upload ./your_data_directory
# use --publish to publish immediately
# ae-upload upload ./your_data_directory --publish
```

Place `metadata.json` in the data directory, or pass it with `--metadata /path/to/metadata.json`.

For advanced options and troubleshooting, see `USER_DOCS.md`.
