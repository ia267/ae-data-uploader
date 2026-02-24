from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def valid_metadata() -> dict:
    return {
        "title": "Validation Test Dataset",
        "description": "Detailed dataset description for schema validation tests.",
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                }
            }
        ],
        "publication_date": "2026-01-15",
        "resource_type": {"id": "dataset"},
        "domain": {
            "discipline": "fluid_dynamics",
            "study": {"field": "jet", "keywords": ["turbulence", "jet"]},
            "observations": [
                {
                    "observation_type": "numerical",
                    "facility": "Test Solver",
                    "observed_quantities": ["velocity"],
                }
            ],
        },
    }
