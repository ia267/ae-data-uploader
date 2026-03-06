from __future__ import annotations

import pytest

from ae_uploader.client import InvenioClient, create_client_from_env


def test_transform_to_invenio_format_maps_core_metadata(valid_metadata: dict):
    client = InvenioClient("https://example.org", "token")
    payload = client._transform_to_invenio_format(valid_metadata)

    assert payload["metadata"]["title"] == valid_metadata["title"]
    assert payload["metadata"]["description"] == valid_metadata["description"]
    assert payload["metadata"]["publication_date"] == valid_metadata["publication_date"]
    assert payload["metadata"]["resource_type"] == valid_metadata["resource_type"]
    assert payload["custom_fields"]["domain"]["discipline"] == "fluid_dynamics"
    assert "files" not in payload


def test_transform_to_invenio_format_enables_files_section(valid_metadata: dict):
    valid_metadata["domain"]["observations"][0]["files"] = [{"variables": ["u"]}]
    client = InvenioClient("https://example.org", "token")

    payload = client._transform_to_invenio_format(valid_metadata)
    assert payload["files"] == {"enabled": True}


def test_transform_to_invenio_format_preserves_optional_fields(valid_metadata: dict):
    valid_metadata["rights"] = [{"id": "cc-by-4.0"}]
    valid_metadata["funding"] = [{"funder": {"name": "Example Funder"}}]
    valid_metadata["publisher"] = "Imperial College London"
    valid_metadata["version"] = "v1.2"
    valid_metadata["contributors"] = [
        {
            "person_or_org": {
                "type": "personal",
                "given_name": "Grace",
                "family_name": "Hopper",
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
    client = InvenioClient("https://example.org", "token")

    payload = client._transform_to_invenio_format(valid_metadata)
    assert payload["metadata"]["rights"] == valid_metadata["rights"]
    assert payload["metadata"]["funding"] == valid_metadata["funding"]
    assert payload["metadata"]["publisher"] == valid_metadata["publisher"]
    assert payload["metadata"]["version"] == valid_metadata["version"]
    assert payload["metadata"]["contributors"] == valid_metadata["contributors"]
    assert payload["metadata"]["related_identifiers"] == valid_metadata["related_identifiers"]


def test_create_client_from_env_requires_url(monkeypatch):
    monkeypatch.delenv("INVENIO_URL", raising=False)
    monkeypatch.setenv("INVENIO_TOKEN", "token")

    with pytest.raises(ValueError, match="INVENIO_URL"):
        create_client_from_env()


def test_create_client_from_env_requires_token(monkeypatch):
    monkeypatch.setenv("INVENIO_URL", "https://example.org")
    monkeypatch.delenv("INVENIO_TOKEN", raising=False)

    with pytest.raises(ValueError, match="INVENIO_TOKEN"):
        create_client_from_env()


def test_create_client_from_env_builds_client(monkeypatch):
    monkeypatch.setenv("INVENIO_URL", "https://example.org")
    monkeypatch.setenv("INVENIO_TOKEN", "token")

    client = create_client_from_env()

    assert client.base_url == "https://example.org"
    assert client.access_token == "token"
    assert client.custom_field_namespace == "domain"
