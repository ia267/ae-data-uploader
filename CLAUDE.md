# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AE Uploader is a Python CLI tool for uploading aeronautics research data to Invenio-RDM repositories with comprehensive metadata validation. It supports fluid mechanics and structural mechanics research data for the Department of Aeronautics at Imperial College London.

## Build & Development Commands

```bash
# Install in development mode
pip install -e .

# Install with dev tools (pytest, black, flake8, mypy)
pip install -e ".[dev]"

# Run the CLI
ae-upload <command>

# Available commands
ae-upload configure      # Interactive credential setup
ae-upload upload <dir>   # Upload dataset directory
ae-upload validate <file> # Validate metadata JSON
ae-upload generate <type> # Generate metadata template (numerical/experimental)
ae-upload schema         # Export JSON schema
ae-upload info           # Show configuration status
```

## Code Architecture

### Source Layout (`src/ae_uploader/`)

- **cli.py** - Click-based CLI with all commands. Entry point via `main()` function. Handles credential management, file operations, and user interaction.

- **client.py** - `InvenioClient` class for Invenio-RDM API interactions. Handles draft creation, file upload (zip or individual), and publishing. Uses Bearer token auth.

- **validate.py** - JSON Schema validation with helpful error hints. Core function is `validate_metadata()`. Uses Draft 7 JSON Schema.

- **schemas/domain.py** - Marshmallow schemas for domain-specific metadata. Contains `to_invenio_custom_fields()` and `from_invenio_custom_fields()` for format conversion.

- **schemas/fluid_dynamics_schema.json** - JSON Schema defining metadata structure. Required fields include title, description, creators, publication_date, resource_type, and domain section.

### Data Flow

1. User provides metadata.json + data files in a directory
2. CLI loads and validates metadata against JSON schema
3. InvenioClient creates draft record via API
4. Files uploaded (zipped by default)
5. Draft is linked to the configured community for review

### Key Patterns

- **Configuration priority**: CLI options → environment variables → user config store → interactive prompts
- **Custom field namespace**: Domain metadata stored in Invenio's `custom_fields` under configurable namespace (default: "domain")
- **Credential storage**: user config directory plus system credential store when available; protected user config fallback otherwise

## Environment Variables

```bash
INVENIO_URL              # Base URL of Invenio instance
INVENIO_TOKEN            # Personal access token
CUSTOM_FIELD_NAMESPACE   # Custom field namespace (default: "domain")
```

## Domain Model

The metadata schema supports two disciplines (`fluid_dynamics`, `structures`) with observations that can be `numerical` or `experimental`. Each observation contains facility info, methods, observed quantities, and optional file metadata with variable descriptions and units.

Valid study fields: `jet`, `boundary_layer`, `wake`, `combustion`, `other`
