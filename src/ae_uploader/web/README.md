# Web-Based Metadata Generator

This HTML form provides a user-friendly interface for generating metadata.json files for research data without using the command line.

## Usage

### Open Locally

Open `src/ae_uploader/web/metadata_form.html` directly in your browser.

## Workflow

1. **Fill Form**: Open the HTML form and fill in your dataset details
   - Core metadata (title, description, date)
   - Creators (add multiple with + button)
   - Domain information (discipline, field, keywords)
   - Observations (numerical or experimental)
   - Optional: License information

2. **Download JSON**: Click "Download metadata.json"
   - Browser will download the generated file

3. **Save to Data Folder**: Move the downloaded `metadata.json` to your data directory
   ```bash
   mv ~/Downloads/metadata.json /path/to/my_simulation_data/
   ```

4. **Upload via CLI**: Use the ae-upload tool
   ```bash
   cd /path/to/my_simulation_data
   ae-upload upload .          # creates draft by default
   # ae-upload upload . --publish
   ```

## Features

- **Dynamic Fields**: Add multiple creators and observations
- **Smart Validation**: Required fields marked with asterisk (*)
- **Dropdown Menus**: Pre-populated with valid values from schema
- **Keyword Autocomplete**: Suggests canonical keywords as users type
- **Keyword Normalisation**: Deduplicates common variants (e.g., `high-Re` vs `high Re`)
- **Conditional Sections**: File information appears for both numerical and experimental
- **Real-time Preview**: Form validates as you type
- **Mobile Responsive**: Works on phones and tablets
- **No Installation**: Pure HTML/CSS/JavaScript, no dependencies

## Form Sections

### Core Metadata
- Title (3-255 characters)
- Description (minimum 10 characters)
- Publication Date
- Resource Type (dataset, publication, software, other)

### Creators
- First Name
- Last Name
- Affiliation (optional)
- Add multiple creators with "+ Add Creator" button

### Domain Information
- Discipline (fluid_dynamics, structures)
- Field (jet, boundary_layer, wake, combustion, other)
- Keywords (comma-separated)
- Flow Regime (optional)

### Observations
- Observation Type (numerical, experimental)
- Facility/Code Name
- Observed Quantities (comma-separated)
- Methods (optional, comma-separated)
- File Information (optional):
  - File name pattern
  - File type
  - Variables
  - Storage format

### License (Optional)
- Creative Commons licenses
- MIT
- Or leave blank

## Tips

1. Required fields: All fields marked with * must be filled
2. Keywords: Use comma-separated values; suggestions/autocomplete appear as you type
3. Multiple items: Use "+ Add" buttons for multiple creators or observations
4. File patterns: Use wildcards like `data_*.vtk` for file name patterns
5. Validation: The browser will highlight any validation errors before download

## Comparison with CLI

| Feature | Web Form | CLI (`ae-upload generate`) |
|---------|----------|---------------------------|
| Interface | Browser-based GUI | Terminal |
| Learning Curve | Intuitive | Requires CLI knowledge |
| Speed | Slower (clicking) | Faster (for experts) |
| Validation | Real-time | On upload |
| Offline | Works offline | Works offline |
| Automation | Manual only | Scriptable |

Both methods produce identical `metadata.json` files that work with `ae-upload upload`.

## Troubleshooting

Download doesn't start:
- Check browser download settings
- Some browsers may block automatic downloads
- Try right-click --> "Save Link As"

Form validation errors:
- Required fields must be filled (marked with *)
- Title must be 3-255 characters
- Description must be at least 10 characters
- At least one creator required
- At least one observation required

JSON file not working with ae-upload:
- Ensure you saved it as `metadata.json`
- Verify it's in the same directory as your data files
- Run `ae-upload validate metadata.json` to check for issues
