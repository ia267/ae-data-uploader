# AE Uploader

A Python CLI tool for uploading aeronautics research data to InvenioRDM repositories with comprehensive metadata validation.

Designed for the Department of Aeronautics at Imperial College London, this tool supports:
- **Fluid Mechanics**: CFD simulations and experimental flow measurements
- **Structural Mechanics**: Numerical simulations and experimental structural tests

## Features

- Metadata Validation: Validates metadata against a strict JSON schema before upload  
- Custom Schema Support: Export and modify schemas for institutional requirements  
- Multi-Discipline Support: Fluid mechanics and structural mechanics disciplines  
- Department-Wide: Designed for all aeronautics research data at Imperial College London  
- Smart Packaging: Automatically zips directories or uploads files individually  
- Direct Upload: Seamless integration with InvenioRDM API  
- CLI Interface: Simple command-line interface for quick operations  
- Template Generation: Create metadata templates for numerical or experimental data  
- Web Form Option: Browser-based form for metadata generation

## Installation

### Quick Install (Development Mode)

```bash
cd ae-data-uploader
pip install -e .
```

### Standard Install

```bash
pip install ae-uploader
```

## Quick Start

### 1. Set Up Credentials

The easiest way is to run the interactive configuration:

```bash
ae-upload configure
```

This will:
- Prompt for your InvenioRDM instance URL
- Prompt for your access token (input hidden)
- Test the connection
- Save credentials to `.env` file

Alternatively, you can create a `.env` file manually:

```bash
INVENIO_URL=https://your-invenio-instance.org
INVENIO_TOKEN=your_access_token_here
CUSTOM_FIELD_NAMESPACE=domain  # Optional, defaults to 'domain'
```

Or the tool will prompt you for credentials when needed.

### 2. Generate a Metadata Template

**Option A: Command-Line (Terminal)**

```bash
ae-upload generate numerical
```

For experimental data:

```bash
ae-upload generate experimental
```

This creates a `metadata.json` file with the required structure.

**Option B: Web Form (Browser)**

Open `web/metadata_form.html` in your browser for a user-friendly form:

```bash
firefox web/metadata_form.html
# or open in any browser
```

Fill out the form, click "Download metadata.json", and save it to your data folder.

See [web/README.md](web/README.md) for detailed instructions.

### 3. Edit Your Metadata

Edit `metadata.json` with your dataset details:

```json
{
  "title": "My Fluid Dynamics Dataset",
  "description": "Detailed description...",
  "creators": [{
    "person_or_org": {
      "type": "personal",
      "given_name": "John",
      "family_name": "Doe"
    },
    "affiliations": [{"name": "Your Institution"}]
  }],
  "publication_date": "2025-12-18",
  "resource_type": {"id": "dataset"},
  "domain": {
    "discipline": "fluid_dynamics",
    "study": {
      "field": "jet",
      "keywords": ["turbulence", "LES"]
    },
    "observations": [{
      "observation_type": "numerical",
      "facility": "Your Code Name",
      "observed_quantities": ["velocity", "pressure"]
    }]
  }
}
```

### 4. Validate Your Metadata

```bash
ae-upload validate metadata.json
```

### 5. Upload Your Data

```bash
ae-upload upload ./my_data_directory
```

The tool will:
1. Find `metadata.json` in the directory
2. Validate against the schema
3. Create a draft in InvenioRDM
4. Upload all files as a zip archive
5. Publish the record

## CLI Commands

### `configure`

Set up InvenioRDM credentials interactively.

```bash
ae-upload configure
```

This command will:
- Prompt for your Invenio instance URL
- Prompt for your access token (securely, with hidden input)
- Test the connection
- Save credentials to `.env` in current directory

**Example:**

```bash
$ ae-upload configure
==================================================
InvenioRDM Credentials Setup
==================================================

Step 1: InvenioRDM Instance URL
  Example: https://invenio.example.org

Enter URL: https://my-invenio.org

Step 2: Access Token
  You can create a token at:
  https://my-invenio.org/account/settings/applications/tokens/new/

Enter access token: ********
Confirm access token: ********

[INFO] Testing connection...
[OK] Connection successful!
[OK] Credentials saved to /path/to/.env
```

### `upload`

Upload a dataset directory to InvenioRDM.

```bash
ae-upload upload <data_directory> [OPTIONS]

Options:
  --token, -t TEXT         Invenio access token
  --url, -u TEXT           Invenio base URL
  --namespace, -n TEXT     Custom field namespace (default: domain)
  --metadata, -m PATH      Path to metadata.json
  --schema, -s PATH        Path to custom JSON schema file
  --no-zip                 Upload files individually
  --draft-only             Create draft without publishing
  --env-file PATH          Path to .env file
  --save-credentials       Save credentials to .env
```

**Examples:**

```bash
# Basic upload (prompts for credentials if not in .env)
ae-upload upload ./simulation_data

# Upload and save credentials for future use
ae-upload upload ./data --save-credentials

# With explicit credentials
ae-upload upload ./data --token TOKEN --url https://invenio.example.org

# Upload files individually (no zip)
ae-upload upload ./data --no-zip

# Create draft only (don't publish)
ae-upload upload ./data --draft-only

# Upload with custom schema validation
ae-upload upload ./data --schema custom_schema.json
```

**Credential Priority:**
1. Command-line options (`--token`, `--url`, `--namespace`)
2. Environment variables (`INVENIO_TOKEN`, `INVENIO_URL`, `CUSTOM_FIELD_NAMESPACE`)
3. `.env` file in current directory
4. Interactive prompts (if none of the above)

### `validate`

Validate metadata against the schema.

```bash
ae-upload validate <metadata_file> [OPTIONS]

Options:
  --verbose, -v          Show detailed information
  --schema, -s PATH      Path to custom JSON schema file
```

**Examples:**

```bash
ae-upload validate metadata.json
ae-upload validate metadata.json --verbose
ae-upload validate metadata.json --schema custom_schema.json
```

### `generate`

Generate a metadata template.

```bash
ae-upload generate <observation_type> [OPTIONS]

Types: numerical, experimental

Options:
  --output, -o PATH    Output file path (default: metadata.json)
```

**Examples:**

```bash
ae-upload generate numerical
ae-upload generate experimental --output my_metadata.json
```

### `schema`

Export the default JSON schema for modification.

```bash
ae-upload schema [OPTIONS]

Options:
  --output, -o PATH    Output file path (default: schema.json)
```

**Examples:**

```bash
# Export default schema
ae-upload schema

# Export to custom location
ae-upload schema --output my_schema.json
```

**Use Case:** Export the default schema, modify it to add custom fields or constraints specific to your Invenio instance, then use it for validation and upload.

### `info`

Show configuration and available options.

```bash
ae-upload info
```

Shows:
- Current credential configuration status
- Supported disciplines, fields, and observation types
- Suggestion to run `configure` if credentials not set

## Custom Schema Support

The uploader supports custom JSON schemas, allowing you to adapt validation to your specific Invenio instance requirements.

### Why Use Custom Schemas?

- **Institutional Requirements**: Different Invenio instances may require different custom fields
- **Stricter Validation**: Add more specific constraints (e.g., regex patterns, value ranges)
- **Additional Fields**: Include fields specific to your research domain or institution
- **Schema Evolution**: Update validation rules without waiting for package updates

### Workflow

```bash
# 1. Export the default schema
ae-upload schema -o my_schema.json

# 2. Modify my_schema.json to add your custom requirements
#    - Add new required fields
#    - Modify enum values
#    - Add pattern validations
#    - Adjust min/max constraints

# 3. Validate your metadata against the custom schema
ae-upload validate metadata.json --schema my_schema.json

# 4. Upload with custom schema validation
ae-upload upload ./data --schema my_schema.json
```

### Example: Adding Custom Fields

After exporting the schema, you can add institution-specific fields:

```json
{
  "properties": {
    "custom_fields": {
      "properties": {
        "institution_id": {
          "type": "string",
          "pattern": "^INST-[0-9]{5}$",
          "description": "Institutional project ID"
        }
      },
      "required": ["institution_id"]
    }
  }
}
```

### Example: Stricter Validation

Restrict keywords to a controlled vocabulary:

```json
{
  "properties": {
    "domain": {
      "properties": {
        "study": {
          "properties": {
            "keywords": {
              "items": {
                "enum": ["turbulence", "LES", "DNS", "RANS", "PIV", "hot-wire"]
              }
            }
          }
        }
      }
    }
  }
}
```

### Best Practices

1. **Start with Default**: Always export and modify the default schema rather than creating from scratch
2. **Test First**: Use `validate` command to test your custom schema before uploading
3. **Document Changes**: Add comments (in a separate file) explaining your modifications
4. **Version Control**: Keep custom schemas in version control alongside your data
5. **Backup**: Keep the original exported schema as reference

## Metadata Schema

The tool validates metadata against a comprehensive JSON schema for aeronautics research, covering both fluid mechanics and structural mechanics disciplines.

### Required Fields

#### Core Metadata
- `title`: Dataset title (3-255 characters)
- `description`: Detailed description (min 10 characters)
- `creators`: Array of at least one creator with `person_or_org` details
- `publication_date`: Date in YYYY-MM-DD format
- `resource_type`: Object with `id` field (e.g., "dataset")

#### Domain Section
- `domain.discipline`: Must be "fluid_dynamics" or "structures"
- `domain.study`: Study metadata
  - `field`: One of: jet, boundary_layer, wake, combustion, other
  - `keywords`: Array of keywords (min 1)
- `domain.observations`: Array of at least one observation
  - `observation_type`: "numerical" or "experimental"
  - `facility`: Name of facility, code, or wind tunnel
  - `observed_quantities`: Array of measured/simulated quantities

### Optional Fields

#### Study Fields
- `subfield`: Array of subfields
- `regime`: Flow regime (e.g., "compressible", "turbulent")
- `model`: Model or case name

#### Observation Fields
- `methods`: Array of methods (e.g., ["LES", "PIV"])
- `data_acquisition_settings`: e.g., "time_resolved", "steady"
- `operating_conditions`: Object with condition key-value pairs
- `model_description`: Description of setup
- `coordinate_system`: Coordinate system description
- `files`: Array of file metadata objects

#### File Metadata
- `file_name`: File name or pattern
- `file_type`: File type (vtk, csv, hdf5, etc.)
- `multiple_files_rule`: Rule for multiple files
- `variables`: Array of variable names (required if files present)
- `variable_description`: Object mapping variable names to descriptions
- `variable_units`: Object mapping variable names to units
- `storage_format`: "binary" or "ASCII"
- `description`: File description
- `example_code`: URL or code snippet

### Rights and Funding
- `rights`: Array of license objects
- `funding`: Array of funding information

## Project Structure

```
ae-data-uploader/
├── pyproject.toml                     # Package configuration
├── README.md                          # This file
├── QUICKSTART.md                      # Quick start guide
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore rules
├── src/
│   └── ae_uploader/
│       ├── __init__.py                # Package initialization
│       ├── cli.py                     # Command-line interface
│       ├── validate.py                # Metadata validation
│       ├── client.py                  # Invenio API client
│       └── schemas/
│           └── fluid_dynamics_schema.json  # JSON Schema
└── examples/
    ├── metadata_numerical_les.json    # Numerical example
    ├── metadata_experimental_piv.json # Experimental example
    └── .env.example                   # Environment template
```

## Invenio Configuration

### Custom Field Namespace

The uploader stores domain-specific metadata in Invenio's `custom_fields` section. By default, it uses the namespace `domain`, but this can be customized if your Invenio instance uses a different namespace.

**Important:** Your InvenioRDM instance must have this custom field configured. Contact your Invenio administrator to ensure the namespace is registered in `invenio.cfg`:

```python
from invenio_records_resources.services.custom_fields import CustomField
from invenio_records_resources.services.custom_fields.mappings import MappingField

RDM_CUSTOM_FIELDS = [
    CustomField(
        name="domain",  # Must match CUSTOM_FIELD_NAMESPACE
        field_cls=MappingField,
        multiple=False,
    )
]
```

**Configuring Custom Namespace:**

1. Via environment variable:
   ```bash
   export CUSTOM_FIELD_NAMESPACE=my_namespace
   ```

2. Via `.env` file:
   ```bash
   CUSTOM_FIELD_NAMESPACE=my_namespace
   ```

3. Via command-line:
   ```bash
   ae-upload upload ./data --namespace my_namespace
   ```

4. During interactive configuration:
   ```bash
   ae-upload configure
   # Will prompt for namespace (defaults to 'domain')
   ```

## Advanced Usage

### Using as a Python Library

```python
from ae_uploader import InvenioClient, validate_metadata
import json

# Load and validate metadata
with open('metadata.json') as f:
    metadata = json.load(f)

is_valid, errors = validate_metadata(metadata)

if is_valid:
    # Create client with custom namespace
    client = InvenioClient(
        base_url='https://invenio.example.org',
        access_token='your_token',
        custom_field_namespace='domain'  # Optional, defaults to 'domain'
    )
    
    # Create draft
    draft = client.create_draft(metadata)
    
    # Upload files
    client.upload_directory(draft['id'], './data')
    
    # Publish
    record = client.publish_draft(draft['id'])
    print(f"Published: {record['id']}")
else:
    print("Validation errors:", errors)
```

### Custom Schema Validation

```python
from ae_uploader.validate import validate_metadata
import json

# Load custom schema
with open('my_schema.json') as f:
    custom_schema = json.load(f)

# Validate against custom schema
is_valid, errors = validate_metadata(metadata, schema=custom_schema)
```

## Troubleshooting

### Connection Issues

```bash
# Test your connection
ae-upload info

# Verify credentials
curl -H "Authorization: Bearer YOUR_TOKEN" https://your-invenio.org/api/records
```

### Validation Errors

Run validation with verbose output:

```bash
ae-upload validate metadata.json --verbose
```

Common issues:
- **Missing required fields**: Check that all required fields are present
- **Invalid date format**: Use YYYY-MM-DD format
- **Invalid enum value**: Check that values match allowed options in schema
- **Missing observation**: At least one observation is required
- **Missing domain section**: The domain section with study and observations is required

### Upload Failures

- Ensure your token has upload permissions
- Check file sizes (Invenio may have limits)
- Verify network connectivity
- Check Invenio instance logs for server-side errors

## Requirements

- Python >= 3.8
- click >= 8.0.0
- requests >= 2.28.0
- jsonschema >= 4.17.0
- pyyaml >= 6.0
- python-dotenv >= 1.0.0

## License

MIT License - see LICENSE file for details.
