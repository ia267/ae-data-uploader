# Quick Start Guide

Get up and running with AE Uploader in 5 minutes!

## Installation

```bash
cd ae-data-uploader
pip install -e .
```

## Step 1: Configure Credentials (1 min)

Run the interactive configuration:

```bash
ae-upload configure
```

This will prompt you for:
- Your Invenio-RDM instance URL
- Your access token (you can create one at: your-invenio.org/account/settings/applications/tokens/new/)

The credentials will be saved to `.env` in the current directory.

**Alternative:** If you prefer not to save credentials, the tool will prompt you each time you run a command.

## Step 2: Generate Metadata Template (1 min)

```bash
ae-upload generate OpenFOAM
```

This creates `metadata.json` in your current directory.

## Step 3: Edit Metadata (2 min)

Open `metadata.json` and fill in your simulation details:

```json
{
  "title": "Your Simulation Title",
  "description": "Detailed description...",
  "creators": [{"name": "Your Name", "affiliation": "Your Org"}],
  "solver": "OpenFOAM",
  "openfoam_specific": {
    "application": "simpleFoam",
    "turbulence_model": "kOmegaSST"
  }
}
```

## Step 4: Validate (30 sec)

```bash
ae-upload validate metadata.json
```

Fix any errors reported.

## Step 5: Upload (30 sec)

```bash
ae-upload upload ./your_simulation_directory
```

Done! Your data is now in Invenio-RDM.

## Common Commands

```bash
# Check configuration
ae-upload info

# Generate template for different solver
ae-upload generate Nektar++

# Create draft without publishing
ae-upload upload ./data --draft-only

# Upload files individually (not zipped)
ae-upload upload ./data --no-zip
```

## Example Metadata Files

Check the `examples/` directory for complete examples:

- `metadata_openfoam.json` - OpenFOAM RANS simulation
- `metadata_nektar.json` - Nektar++ DNS simulation  
- `metadata_su2.json` - SU2 transonic flow simulation

## Troubleshooting

**"Cannot connect to Invenio"**
- Run `ae-upload configure` to set up credentials again
- Verify your URL is correct (no trailing slash)
- Check your token has 'deposit:write' permissions

**"Validation failed"**
- Run `ae-upload validate metadata.json --verbose` to see specific errors
- Check that all required fields are present
- Make sure discipline, field, and observation_type values are valid

**Forgot to configure?**
- Don't worry! The tool will prompt you for credentials when needed
- Or run `ae-upload configure` anytime to set them up

## Need Help?

- Full documentation: See `README.md`
- Examples: See `examples/` directory
- Issues: Open a GitHub issue
