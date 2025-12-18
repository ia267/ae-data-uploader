# Web-Based Metadata Generator

This HTML form provides a user-friendly interface for generating metadata.json files for research data without using the command line.

Supports both fluid mechanics and structural mechanics datasets.

## Usage

### Option 1: Open Locally

Simply open `metadata_form.html` in your web browser:

```bash
# From the web directory
firefox metadata_form.html
# or
google-chrome metadata_form.html
# or
open metadata_form.html  # macOS
```

### Option 2: Serve with Python

```bash
# From the web directory
python3 -m http.server 8000
```

Then visit: http://localhost:8000/metadata_form.html

### Option 3: Deploy to Web Server

Upload `metadata_form.html` to your web server or GitHub Pages. The form runs entirely in the browser (no server-side processing needed).

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
   ae-upload upload .
   ```

## Features

- **Dynamic Fields**: Add multiple creators and observations
- **Smart Validation**: Required fields marked with asterisk (*)
- **Dropdown Menus**: Pre-populated with valid values from schema
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

1. **Required Fields**: All fields marked with * must be filled
2. **Keywords**: Use comma-separated values (e.g., "turbulence, LES, high-speed")
3. **Multiple Items**: Use "+ Add" buttons for multiple creators or observations
4. **File Patterns**: Use wildcards like `data_*.vtk` for file name patterns
5. **Validation**: The browser will highlight any validation errors before download

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

## Browser Compatibility

- Chrome/Edge: ✓ Fully supported
- Firefox: ✓ Fully supported
- Safari: ✓ Fully supported
- Mobile browsers: ✓ Responsive design

## Troubleshooting

**Download doesn't start:**
- Check browser download settings
- Some browsers may block automatic downloads
- Try right-click → "Save Link As"

**Form validation errors:**
- Required fields must be filled (marked with *)
- Title must be 3-255 characters
- Description must be at least 10 characters
- At least one creator required
- At least one observation required

**JSON file not working with ae-upload:**
- Ensure you saved it as `metadata.json`
- Verify it's in the same directory as your data files
- Run `ae-upload validate metadata.json` to check for issues
