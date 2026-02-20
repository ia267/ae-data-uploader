"""Fluid dynamics domain-specific schemas."""

from marshmallow import Schema, fields, validate


class FileMetadataSchema(Schema):
    """Schema for file metadata (Level 3)."""
    
    file_name = fields.Str()
    file_type = fields.Str()
    multiple_files_rule = fields.Str()
    variables = fields.List(fields.Str(), required=True)  # Required if files are provided
    variable_description = fields.Dict(keys=fields.Str(), values=fields.Str())
    variable_units = fields.Dict(keys=fields.Str(), values=fields.Str())  # Per-variable units: {"u": "m/s", "p": "Pa"}
    storage_format = fields.Str()
    description = fields.Str()
    example_code = fields.Str()


class ObservationSchema(Schema):
    """Schema for observation metadata (Level 2)."""
    
    observation_type = fields.Str(
        required=True, 
        validate=validate.OneOf(["numerical", "experimental"])
    )  # MANDATORY: numerical or experimental
    facility = fields.Str(required=True)  # MANDATORY: provenance
    methods = fields.List(fields.Str())
    data_acquisition_settings = fields.Str()
    operating_conditions = fields.Dict(keys=fields.Str(), values=fields.Raw())
    observed_quantities = fields.List(fields.Str(), required=True)  # MANDATORY: what was measured/simulated
    model_description = fields.Str()
    coordinate_system = fields.Str()
    files = fields.List(fields.Nested(FileMetadataSchema))


class StudyMetadataSchema(Schema):
    """Schema for study metadata (Level 1)."""
    
    field = fields.Str(
        required=True, 
        validate=validate.OneOf([
            "jet", "boundary_layer", "wake", "combustion", "other"
        ])
    )  # MANDATORY: controlled vocabulary
    subfield = fields.List(fields.Str())
    regime = fields.Str()
    model = fields.Str()  # Optional: not all studies have named models
    keywords = fields.List(fields.Str(), required=True)  # MANDATORY: minimum metadata for discovery


class FluidDynamicsSchema(Schema):
    """Complete fluid dynamics domain schema."""
    
    discipline = fields.Str(
        required=True, 
        validate=validate.OneOf(["fluid_dynamics"])
    )  # MANDATORY: fluid-only controlled vocabulary
    study = fields.Nested(StudyMetadataSchema, required=True)  # MANDATORY: must have study info
    observations = fields.List(fields.Nested(ObservationSchema), required=True)  # MANDATORY: must have at least one observation


def to_invenio_custom_fields(data: dict, namespace: str = "domain") -> dict:
    """
    Convert domain schema to Invenio custom fields format.
    
    Args:
        data: Dictionary validated against FluidDynamicsSchema
        namespace: Custom field namespace (default: "domain")
    
    Returns:
        Dictionary with nested custom fields for Invenio API
    
    Example:
        >>> data = {
        ...     "discipline": "fluid_dynamics",
        ...     "study": {
        ...         "field": "jet",
        ...         "keywords": ["turbulence", "mixing"],
        ...         "regime": "subsonic"
        ...     }
        ... }
        >>> to_invenio_custom_fields(data)
        {
            "domain": {
                "discipline": "fluid_dynamics",
                "study": {
                    "field": "jet",
                    "keywords": ["turbulence", "mixing"],
                    "regime": "subsonic"
                }
            }
        }
    """
    # Invenio custom fields for this deployment are configured as:
    # custom_fields.<namespace> = { ...domain metadata... }
    return {namespace: data}


def from_invenio_custom_fields(custom_fields: dict, namespace: str = "domain") -> dict:
    """
    Convert Invenio custom fields back to domain schema format.
    
    Args:
        custom_fields: Dictionary from Invenio record's custom_fields
        namespace: Custom field namespace (default: "domain")
    
    Returns:
        Dictionary compatible with FluidDynamicsSchema
    """
    # Preferred format: nested under custom_fields.<namespace>.
    nested = custom_fields.get(namespace)
    if isinstance(nested, dict):
        return nested

    # Backward-compatible fallback for legacy flattened keys.
    data = {}

    discipline_key = f"{namespace}:discipline"
    if discipline_key in custom_fields:
        data["discipline"] = custom_fields[discipline_key]

    study = {}
    study_prefix = f"{namespace}:study:"
    for key, value in custom_fields.items():
        if key.startswith(study_prefix):
            field_name = key[len(study_prefix):]
            if field_name == "subfield" and isinstance(value, str):
                study[field_name] = [s.strip() for s in value.split(",")]
            else:
                study[field_name] = value

    if study:
        data["study"] = study

    return data
