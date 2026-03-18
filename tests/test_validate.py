from __future__ import annotations

import json

import pytest

from ae_uploader.validate import (
    load_schema,
    validate_metadata,
    validate_metadata_file,
    validate_with_hints,
)


def test_load_schema_returns_document():
    schema = load_schema()
    assert schema["type"] == "object"
    assert "domain" in schema["properties"]


def test_validate_metadata_accepts_valid_payload(valid_metadata: dict):
    is_valid, errors = validate_metadata(valid_metadata)
    assert is_valid is True
    assert errors == []


def test_validate_metadata_accepts_contributors_and_related_identifiers(valid_metadata: dict):
    valid_metadata["contributors"] = [
        {
            "person_or_org": {
                "type": "personal",
                "given_name": "Grace",
                "family_name": "Hopper",
                "identifiers": [
                    {
                        "scheme": "orcid",
                        "identifier": "0000-0002-1825-0097",
                    }
                ],
            },
            "role": {"id": "datacurator"},
        }
    ]
    valid_metadata["related_identifiers"] = [
        {
            "identifier": "10.9999/example",
            "scheme": "doi",
            "relation_type": {"id": "ispartof"},
            "resource_type": {"id": "publication"},
        }
    ]

    is_valid, errors = validate_metadata(valid_metadata)
    assert is_valid is True
    assert errors == []


def test_validate_metadata_accepts_multiple_regimes(valid_metadata: dict):
    valid_metadata["domain"]["study"]["regime"] = ["compressible", "high_Re"]

    is_valid, errors = validate_metadata(valid_metadata)
    assert is_valid is True
    assert errors == []


def test_validate_metadata_rejects_invalid_orcid(valid_metadata: dict):
    valid_metadata["creators"][0]["person_or_org"]["identifiers"] = [
        {
            "scheme": "orcid",
            "identifier": "0000-0000-0000-0000",
        }
    ]

    is_valid, errors = validate_metadata(valid_metadata)
    assert is_valid is False
    assert any("Invalid ORCID identifier" in error for error in errors)


def test_validate_metadata_rejects_missing_required_field(valid_metadata: dict):
    valid_metadata.pop("title")
    is_valid, errors = validate_metadata(valid_metadata)
    assert is_valid is False
    assert any("title" in error for error in errors)


def test_validate_with_hints_reports_domain_guidance(valid_metadata: dict):
    valid_metadata["domain"]["discipline"] = "invalid_discipline"
    valid_metadata["domain"]["study"]["field"] = "invalid_field"

    is_valid, errors, hints = validate_with_hints(valid_metadata)

    assert is_valid is False
    assert errors
    assert any("discipline" in hint.lower() for hint in hints)
    assert any("field" in hint.lower() for hint in hints)


def test_validate_metadata_file_raises_for_missing_file(tmp_path):
    missing = tmp_path / "missing_metadata.json"
    with pytest.raises(FileNotFoundError):
        validate_metadata_file(str(missing))


def test_validate_metadata_file_raises_for_invalid_json(tmp_path):
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        validate_metadata_file(str(metadata_file))
