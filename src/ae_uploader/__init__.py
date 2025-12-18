"""
AE Uploader - CLI tool for uploading fluid dynamics data to Invenio-RDM.

This package provides functionality to:
- Validate metadata against a JSON schema
- Package data files with metadata
- Upload to Invenio-RDM repositories
"""

try:
    from importlib.metadata import version
    __version__ = version("ae-uploader")
except Exception:
    # Fallback for development installations
    __version__ = "0.1.0"

__author__ = "AE Research Team"

from .validate import validate_metadata
from .client import InvenioClient

__all__ = ["validate_metadata", "InvenioClient", "__version__"]
