"""Schema package initialization."""

from .domain import (
    FluidDynamicsSchema,
    StudyMetadataSchema,
    ObservationSchema,
    FileMetadataSchema,
    to_invenio_custom_fields,
    from_invenio_custom_fields,
)

__all__ = [
    "FluidDynamicsSchema",
    "StudyMetadataSchema",
    "ObservationSchema",
    "FileMetadataSchema",
    "to_invenio_custom_fields",
    "from_invenio_custom_fields",
]
