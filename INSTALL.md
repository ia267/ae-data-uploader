# AE Uploader - Installation and Testing Guide

## Package Overview

The AE Uploader is now configured with your fluid dynamics domain schema supporting both numerical and experimental observations. All emojis have been removed from the output.

## Installation

```bash
cd ae-data-uploader
pip install -e .
```

## Quick Test

### 1. Check Installation

```bash
ae-upload info
```

Expected output:
```
AE Uploader v0.1.0
==================================================

Configuration:
  INVENIO_URL: Not set
  INVENIO_TOKEN: Not set

[WARNING] Missing configuration. Set environment variables or use --token and --url

Supported disciplines:
  - fluid_dynamics
  - structures

Supported fields:
  - jet
  - boundary_layer
  - wake
  - combustion
  - other

Observation types:
  - numerical
  - experimental
```

### 2. Generate Template

```bash
ae-upload generate numerical
```

This creates `metadata.json` with the fluid dynamics schema structure.

### 3. Validate Template

```bash
ae-upload validate metadata.json --verbose
```

Expected output:
```
[INFO] Validating metadata.json...
[OK] Metadata is valid!

Summary:
  Title: My Fluid Dynamics Dataset
  Discipline: fluid_dynamics
  Creators: 1
```

### 4. Try Example Files

Test with the provided examples:

```bash
# Numerical simulation example
ae-upload validate examples/metadata_numerical_les.json --verbose

# Experimental data example  
ae-upload validate examples/metadata_experimental_piv.json --verbose
```

## Key Changes from Original Request

### Schema Updates
- Changed from CFD-specific to fluid dynamics domain schema
- Supports both `numerical` and `experimental` observation types
- Includes three-level hierarchy: Study -> Observations -> Files
- Matches your Marshmallow schema structure exactly

### Field Mappings
- `discipline`: "fluid_dynamics" or "structures"
- `field`: jet, boundary_layer, wake, combustion, other
- `observation_type`: numerical or experimental
- `facility`: Code name (numerical) or Wind tunnel (experimental)
- `observed_quantities`: Variables measured/simulated

### CLI Changes
- Removed all emoji characters (✓, ✗, 📋, 🚀, etc.)
- Replaced with text indicators: [OK], [ERROR], [INFO], [FAILED], [WARNING], [HINTS]
- Updated `generate` command to use observation_type (numerical/experimental) instead of solver
- Updated `info` command to show disciplines, fields, and observation types

### File Structure
- Schema file: `fluid_dynamics_schema.json` (old `cfd_schema.json` removed)
- Examples updated:
  - `metadata_numerical_les.json` - LES contrails simulation
  - `metadata_experimental_piv.json` - PIV boundary layer measurements
  - Removed: OpenFOAM, Nektar++, SU2 specific examples

## Example Metadata Structure

```json
{
  "title": "Dataset Title",
  "description": "Description",
  "creators": [...],
  "publication_date": "2025-12-18",
  "resource_type": {"id": "dataset"},
  "domain": {
    "discipline": "fluid_dynamics",
    "study": {
      "field": "jet",
      "subfield": ["combustion", "multi-phase"],
      "regime": "compressible",
      "model": "contrails",
      "keywords": ["LES", "turbulence"]
    },
    "observations": [
      {
        "observation_type": "numerical",
        "facility": "BOFFIN",
        "methods": ["LES", "PBE"],
        "observed_quantities": ["velocity", "pressure"],
        "operating_conditions": {
          "Mach": 0.7,
          "Reynolds": 1000000
        },
        "files": [
          {
            "file_name": "data_*.vtk",
            "variables": ["u", "v", "w", "p"],
            "variable_units": {"u": "m/s", "p": "Pa"}
          }
        ]
      }
    ]
  }
}
```

## Testing Upload (When Ready)

### Set Up Environment

```bash
# Create .env file
cat > .env << EOF
INVENIO_URL=https://your-invenio-instance.org
INVENIO_TOKEN=your_access_token
EOF
```

### Upload Data

```bash
# Create draft only (for review)
ae-upload upload ./my_data --draft-only

# Upload and publish
ae-upload upload ./my_data
```

## Schema Validation Features

The schema enforces:
- At least one observation per dataset
- Required fields per observation type
- Valid enumerations for discipline, field, observation_type
- Proper file metadata when files are included
- Variable units and descriptions for data files

## Next Steps

1. Test the installation: `pip install -e .`
2. Generate a template: `ae-upload generate numerical`
3. Edit the template with your data
4. Validate: `ae-upload validate metadata.json`
5. When ready, upload to your Invenio instance

## Support

For questions or issues:
- Check validation output for specific error messages
- Use `--verbose` flag for detailed information
- Review example files in `examples/` directory
- See full documentation in `README.md`
