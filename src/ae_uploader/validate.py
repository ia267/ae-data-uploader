"""
Metadata validation module.

This module provides functions to validate fluid dynamics metadata against the JSON schema.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import jsonschema
from jsonschema import Draft7Validator, validators

# Use importlib.resources for Python 3.9+, fall back to importlib_resources for 3.8
if sys.version_info >= (3, 9):
    from importlib import resources
else:
    try:
        import importlib_resources as resources
    except ImportError:
        resources = None


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def load_schema(schema_name: str = "fluid_dynamics_schema.json") -> Dict[str, Any]:
    """
    Load the JSON schema from the schemas directory.
    
    Args:
        schema_name: Name of the schema file
        
    Returns:
        Dictionary containing the schema
        
    Raises:
        FileNotFoundError: If schema file doesn't exist
    """
    # Try modern importlib.resources first (Python 3.9+)
    if resources is not None:
        try:
            if sys.version_info >= (3, 9):
                schema_files = resources.files("ae_uploader.schemas")
                schema_file = schema_files.joinpath(schema_name)
                with schema_file.open('r') as f:
                    return json.load(f)
            else:
                # Python 3.8 with importlib_resources backport
                with resources.open_text("ae_uploader.schemas", schema_name) as f:
                    return json.load(f)
        except (FileNotFoundError, AttributeError, TypeError):
            pass
    
    # Fallback to file path (for editable installs)
    schema_path = Path(__file__).parent / "schemas" / schema_name
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_name}")
    
    with open(schema_path, 'r') as f:
        return json.load(f)


def validate_metadata(metadata: Dict[str, Any], schema: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
    """
    Validate metadata against the CFD schema.
    
    Args:
        metadata: Dictionary containing the metadata to validate
        schema: Optional schema dictionary. If None, loads default cfd_schema.json
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Example:
        >>> metadata = {"title": "My CFD Sim", ...}
        >>> is_valid, errors = validate_metadata(metadata)
        >>> if not is_valid:
        ...     print("\\n".join(errors))
    """
    if schema is None:
        schema = load_schema()
    
    # Create validator
    validator = Draft7Validator(schema)
    
    # Collect all validation errors
    errors = []
    for error in sorted(validator.iter_errors(metadata), key=lambda e: e.path):
        # Build a readable error message
        path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"[{path}] {error.message}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_metadata_file(metadata_path: str, schema_path: str = None) -> Tuple[bool, List[str]]:
    """
    Validate a metadata JSON file against the schema.
    
    Args:
        metadata_path: Path to the metadata JSON file
        schema_path: Optional path to schema file. If None, uses default.
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Raises:
        FileNotFoundError: If metadata file doesn't exist
        json.JSONDecodeError: If metadata file is not valid JSON
    """
    metadata_file = Path(metadata_path)
    
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    # Load metadata
    with open(metadata_file, 'r') as f:
        try:
            metadata = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in metadata file: {e.msg}",
                e.doc,
                e.pos
            )
    
    # Load schema if custom path provided
    schema = None
    if schema_path:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    
    return validate_metadata(metadata, schema)


def get_required_fields_for_observation(observation_type: str) -> List[str]:
    """
    Get the list of required fields based on observation type.
    
    Args:
        observation_type: Type of observation (numerical or experimental)
        
    Returns:
        List of required field names
    """
    base_fields = [
        "observation_type",
        "facility",
        "observed_quantities"
    ]
    
    return base_fields


def validate_with_hints(metadata: Dict[str, Any], schema: Dict[str, Any] = None) -> Tuple[bool, List[str], List[str]]:
    """
    Validate metadata and provide helpful hints for fixing errors.
    
    Args:
        metadata: Dictionary containing the metadata to validate
        schema: Optional custom schema dictionary
        
    Returns:
        Tuple of (is_valid, error_messages, hints)
    """
    is_valid, errors = validate_metadata(metadata, schema)
    
    hints = []
    
    # Check for common issues and provide hints
    if not is_valid:
        if any("discipline" in err for err in errors):
            hints.append(
                "Valid disciplines: fluid_dynamics, structures"
            )
        
        if any("field" in err for err in errors):
            hints.append(
                "Valid fields: jet, boundary_layer, wake, combustion, other"
            )
        
        if any("observation_type" in err for err in errors):
            hints.append(
                "Valid observation types: numerical, experimental"
            )
        
        if any("observations" in err for err in errors):
            hints.append(
                "At least one observation is required with observation_type, facility, and observed_quantities"
            )
        
        if any("creators" in err for err in errors):
            hints.append(
                "At least one creator with person_or_org details is required"
            )
        
        if any("publication_date" in err for err in errors):
            hints.append(
                "publication_date must be in YYYY-MM-DD format"
            )
        
        if any("domain" in err for err in errors):
            hints.append(
                "Domain section requires: discipline, study (with field and keywords), and observations"
            )
    
    return is_valid, errors, hints


if __name__ == "__main__":
    # Quick test of the validation
    import sys
    
    if len(sys.argv) > 1:
        metadata_file = sys.argv[1]
        print(f"Validating {metadata_file}...")
        
        try:
            is_valid, errors = validate_metadata_file(metadata_file)
            
            if is_valid:
                print("[OK] Metadata is valid!")
            else:
                print("[FAILED] Validation failed:")
                for error in errors:
                    print(f"  {error}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python validate.py <metadata.json>")
