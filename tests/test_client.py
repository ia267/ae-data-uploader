from __future__ import annotations

import pytest
from unittest.mock import Mock

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
    monkeypatch.setenv("CUSTOM_FIELD_NAMESPACE", "domain")
    monkeypatch.setenv("INVENIO_COMMUNITY", "ae-dept-data")
    monkeypatch.setenv("INVENIO_COMMUNITIES", "ae-dept-data,future-lab-data")

    client = create_client_from_env()

    assert client.base_url == "https://example.org"
    assert client.access_token == "token"
    assert client.custom_field_namespace == "domain"
    assert client.community == "ae-dept-data"
    assert client.allowed_communities == ["ae-dept-data", "future-lab-data"]


def test_create_client_from_env_uses_first_allowed_community_as_default(monkeypatch):
    monkeypatch.setenv("INVENIO_URL", "https://example.org")
    monkeypatch.setenv("INVENIO_TOKEN", "token")
    monkeypatch.setenv("INVENIO_COMMUNITIES", "future-lab-data,ae-dept-data")
    monkeypatch.delenv("INVENIO_COMMUNITY", raising=False)

    client = create_client_from_env()

    assert client.community == "future-lab-data"
    assert client.allowed_communities == ["future-lab-data", "ae-dept-data"]


def test_create_client_from_env_treats_single_community_as_allowlist(monkeypatch):
    monkeypatch.setenv("INVENIO_URL", "https://example.org")
    monkeypatch.setenv("INVENIO_TOKEN", "token")
    monkeypatch.setenv("INVENIO_COMMUNITY", "ae-dept-data")
    monkeypatch.delenv("INVENIO_COMMUNITIES", raising=False)

    client = create_client_from_env()

    assert client.community == "ae-dept-data"
    assert client.allowed_communities == ["ae-dept-data"]


def test_create_draft_does_not_set_parent_community(valid_metadata: dict):
    client = InvenioClient("https://example.org", "token", community="ae-dept-data")

    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"id": "12345"}
    client.session.post = Mock(return_value=response)

    client.create_draft(valid_metadata)

    _, kwargs = client.session.post.call_args
    assert "parent" not in kwargs["json"]


def test_submit_draft_for_review_uses_review_then_submit_endpoints():
    client = InvenioClient("https://example.org", "token", community="ae-dept-data")

    detail_response = Mock(status_code=404)
    detail_response.raise_for_status = Mock()
    search_response = Mock(status_code=200)
    search_response.raise_for_status = Mock()
    search_response.json.return_value = {
        "hits": {"hits": [{"id": "comm-123", "slug": "ae-dept-data"}]}
    }
    review_response = Mock()
    review_response.raise_for_status = Mock()
    review_response.json.return_value = {"id": "req-123"}

    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(side_effect=[detail_response, search_response])
    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock(return_value=submit_response)

    result = client.submit_draft_for_review("draft-1")

    assert result == {"id": "req-123"}
    client.session.put.assert_called_once_with(
        "https://example.org/api/records/draft-1/draft/review",
        json={
            "receiver": {"community": "comm-123"},
            "type": "community-submission",
        },
    )
    client.session.post.assert_called_once_with(
        "https://example.org/api/records/draft-1/draft/actions/submit-review",
        json={"require_review": True},
    )


def test_submit_draft_for_review_accepts_optional_comment():
    client = InvenioClient("https://example.org", "token", community="ae-dept-data")

    detail_response = Mock(status_code=404)
    detail_response.raise_for_status = Mock()
    search_response = Mock(status_code=200)
    search_response.raise_for_status = Mock()
    search_response.json.return_value = {
        "hits": {"hits": [{"id": "comm-123", "slug": "ae-dept-data"}]}
    }
    review_response = Mock()
    review_response.raise_for_status = Mock()
    review_response.json.return_value = {"id": "req-456"}

    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(side_effect=[detail_response, search_response])
    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock(return_value=submit_response)

    client.submit_draft_for_review("draft-2", review_comment="please review")

    _, kwargs = client.session.post.call_args
    assert kwargs["json"] == {
        "require_review": True,
        "payload": {
            "content": "please review",
            "format": "html",
        },
    }


def test_submit_draft_for_review_requires_community():
    client = InvenioClient("https://example.org", "token", community="")

    with pytest.raises(ValueError, match="community"):
        client.submit_draft_for_review("draft-3")


def test_submit_draft_for_review_accepts_direct_community_id():
    client = InvenioClient(
        "https://example.org",
        "token",
        community="8ce765f7-2f11-4f47-a740-0d5d4b9d54f0",
    )

    detail_response = Mock(status_code=200)
    detail_response.raise_for_status = Mock()
    detail_response.json.return_value = {
        "id": "8ce765f7-2f11-4f47-a740-0d5d4b9d54f0"
    }
    review_response = Mock()
    review_response.raise_for_status = Mock()
    review_response.json.return_value = {"id": "req-789"}
    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=detail_response)
    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock(return_value=submit_response)

    client.submit_draft_for_review("draft-4")

    client.session.get.assert_called_once_with(
        "https://example.org/api/communities/8ce765f7-2f11-4f47-a740-0d5d4b9d54f0"
    )
    client.session.put.assert_called_once_with(
        "https://example.org/api/records/draft-4/draft/review",
        json={
            "receiver": {"community": "8ce765f7-2f11-4f47-a740-0d5d4b9d54f0"},
            "type": "community-submission",
        },
    )


def test_submit_draft_for_review_rejects_community_outside_allowlist():
    client = InvenioClient(
        "https://example.org",
        "token",
        community="ae-dept-data",
        allowed_communities=["ae-dept-data", "future-lab-data"],
    )
    client._resolve_community_id = Mock(
        side_effect=lambda ref: {
            "other-community": "comm-999",
            "ae-dept-data": "comm-123",
            "future-lab-data": "comm-456",
        }[ref]
    )

    with pytest.raises(ValueError, match="configured allowlist"):
        client.submit_draft_for_review("draft-5", community_id="other-community")


def test_submit_draft_for_review_accepts_equivalent_id_with_allowlist():
    client = InvenioClient(
        "https://example.org",
        "token",
        community="ae-dept-data",
        allowed_communities=["ae-dept-data"],
    )
    client._resolve_community_id = Mock(
        side_effect=lambda ref: {
            "comm-123": "comm-123",
            "ae-dept-data": "comm-123",
        }[ref]
    )

    review_response = Mock()
    review_response.raise_for_status = Mock()
    review_response.json.return_value = {"id": "req-999"}
    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock(return_value=submit_response)

    result = client.submit_draft_for_review("draft-6", community_id="comm-123")

    assert result == {"id": "req-999"}
    client.session.put.assert_called_once_with(
        "https://example.org/api/records/draft-6/draft/review",
        json={
            "receiver": {"community": "comm-123"},
            "type": "community-submission",
        },
    )


def test_resolve_submission_community_rejects_community_outside_allowlist():
    client = InvenioClient(
        "https://example.org",
        "token",
        community="ae-dept-data",
        allowed_communities=["ae-dept-data"],
    )
    client._resolve_community_id = Mock(
        side_effect=lambda ref: {
            "other-community": "comm-999",
            "ae-dept-data": "comm-123",
        }[ref]
    )

    with pytest.raises(ValueError, match="configured allowlist"):
        client.resolve_submission_community("other-community")
