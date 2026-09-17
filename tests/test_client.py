from __future__ import annotations

from pathlib import Path
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

    draft_response = Mock(status_code=200)
    draft_response.raise_for_status = Mock()
    draft_response.json.return_value = {"id": "draft-1", "links": {}}

    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(
        side_effect=[
            detail_response,
            search_response,
            draft_response,
            draft_response,
            draft_response,
        ]
    )
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


def test_set_draft_submission_community_updates_review_state_only():
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
    review_response.json.return_value = {"id": "req-321"}

    draft_response = Mock(status_code=200)
    draft_response.raise_for_status = Mock()
    draft_response.json.return_value = {"id": "draft-1", "links": {}}

    client.session.get = Mock(
        side_effect=[
            detail_response,
            search_response,
            draft_response,
            draft_response,
        ]
    )
    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock()

    result = client.set_draft_submission_community("draft-1")

    assert result == {"id": "req-321"}
    client.session.put.assert_called_once_with(
        "https://example.org/api/records/draft-1/draft/review",
        json={
            "receiver": {"community": "comm-123"},
            "type": "community-submission",
        },
    )
    client.session.post.assert_not_called()


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

    draft_response = Mock(status_code=200)
    draft_response.raise_for_status = Mock()
    draft_response.json.return_value = {"id": "draft-2", "links": {}}

    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(
        side_effect=[
            detail_response,
            search_response,
            draft_response,
            draft_response,
            draft_response,
        ]
    )
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
    draft_response = Mock(status_code=200)
    draft_response.raise_for_status = Mock()
    draft_response.json.return_value = {"id": "draft-4", "links": {}}
    review_response = Mock()
    review_response.raise_for_status = Mock()
    review_response.json.return_value = {"id": "req-789"}
    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(
        side_effect=[
            detail_response,
            draft_response,
            draft_response,
            draft_response,
        ]
    )
    client.session.put = Mock(return_value=review_response)
    client.session.post = Mock(return_value=submit_response)

    client.submit_draft_for_review("draft-4")

    assert client.session.get.call_args_list[0].args[0] == (
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

    draft_response = Mock(status_code=200)
    draft_response.raise_for_status = Mock()
    draft_response.json.return_value = {"id": "draft-6", "links": {}}

    submit_response = Mock()
    submit_response.raise_for_status = Mock()

    client.session.get = Mock(side_effect=[draft_response, draft_response, draft_response])
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


def test_get_link_supports_nested_actions_mapping():
    payload = {
        "links": {
            "actions": {
                "publish": "/api/records/draft-1/draft/actions/publish",
            }
        }
    }

    assert (
        InvenioClient._get_link(payload, "actions.publish")
        == "/api/records/draft-1/draft/actions/publish"
    )


def test_get_link_supports_href_link_objects():
    payload = {
        "links": {
            "actions": {
                "submit_review": {
                    "href": "/api/records/draft-2/draft/actions/submit-review"
                }
            }
        }
    }

    assert (
        InvenioClient._get_link(payload, "actions.submit_review")
        == "/api/records/draft-2/draft/actions/submit-review"
    )


def test_upload_file_uses_entry_links_when_entries_is_dict(tmp_path: Path):
    client = InvenioClient("https://example.org", "token")

    data_file = tmp_path / "data.bin"
    data_file.write_bytes(b"abc")

    draft_payload = {
        "id": "draft-10",
        "links": {"files": "/api/records/draft-10/draft/files"},
    }

    init_response = Mock()
    init_response.raise_for_status = Mock()
    init_response.json.return_value = {
        "entries": {
            "data.bin": {
                "key": "data.bin",
                "links": {
                    "content": "/api/records/draft-10/draft/files/data.bin/content",
                    "commit": "/api/records/draft-10/draft/files/data.bin/commit",
                },
            }
        }
    }

    upload_response = Mock()
    upload_response.raise_for_status = Mock()
    upload_response.content = b"{}"
    upload_response.json.return_value = {}

    commit_response = Mock()
    commit_response.raise_for_status = Mock()
    commit_response.json.return_value = {"key": "data.bin", "status": "completed"}

    client.session.post = Mock(return_value=init_response)
    client.session.put = Mock(return_value=upload_response)
    client._draft_resource = Mock(side_effect=[draft_payload, draft_payload])

    # First post() is file initialisation, second is commit.
    client.session.post.side_effect = [init_response, commit_response]

    result = client.upload_file("draft-10", str(data_file))

    assert result == {"key": "data.bin", "status": "completed"}
    assert client.session.post.call_args_list[0].args[0] == (
        "https://example.org/api/records/draft-10/draft/files"
    )
    assert client.session.post.call_args_list[1].args[0] == (
        "https://example.org/api/records/draft-10/draft/files/data.bin/commit"
    )


def test_upload_file_skips_commit_when_not_advertised(tmp_path: Path):
    client = InvenioClient("https://example.org", "token")

    data_file = tmp_path / "sample.h5"
    data_file.write_bytes(b"1234")

    draft_payload = {
        "id": "draft-11",
        "links": {"files": "/api/records/draft-11/draft/files"},
    }

    init_response = Mock()
    init_response.raise_for_status = Mock()
    init_response.json.return_value = {
        "entries": [
            {
                "key": "sample.h5",
                "links": {
                    "content": "/api/records/draft-11/draft/files/sample.h5/content",
                },
            }
        ]
    }

    upload_response = Mock()
    upload_response.raise_for_status = Mock()
    upload_response.content = b"{}"
    upload_response.json.return_value = {"key": "sample.h5", "status": "uploaded"}

    client._draft_resource = Mock(side_effect=[draft_payload, draft_payload])
    client.session.post = Mock(return_value=init_response)
    client.session.put = Mock(return_value=upload_response)

    result = client.upload_file("draft-11", str(data_file))

    assert result == {"key": "sample.h5", "status": "uploaded"}
    assert client.session.post.call_count == 1


def test_upload_directory_reports_progress_for_uploadable_files(tmp_path: Path):
    client = InvenioClient("https://example.org", "token")
    data_dir = tmp_path / "data"
    nested_dir = data_dir / "nested"
    hidden_dir = data_dir / ".hidden"
    nested_dir.mkdir(parents=True)
    hidden_dir.mkdir()

    (data_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (data_dir / ".secret").write_text("skip", encoding="utf-8")
    (hidden_dir / "hidden.csv").write_text("skip", encoding="utf-8")
    first_file = data_dir / "a.csv"
    second_file = nested_dir / "b.h5"
    first_file.write_text("a", encoding="utf-8")
    second_file.write_text("b", encoding="utf-8")

    client.upload_file = Mock(side_effect=[
        {"key": "a.csv", "status": "uploaded"},
        {"key": "b.h5", "status": "uploaded"},
    ])
    progress = []

    result = client.upload_directory(
        "draft-12",
        str(data_dir),
        create_zip=False,
        progress_callback=lambda file_path, index, total: progress.append(
            (file_path.relative_to(data_dir).as_posix(), index, total)
        ),
    )

    assert result == [
        {"key": "a.csv", "status": "uploaded"},
        {"key": "b.h5", "status": "uploaded"},
    ]
    assert progress == [("a.csv", 1, 2), ("nested/b.h5", 2, 2)]
    assert [call.args[1] for call in client.upload_file.call_args_list] == [
        str(first_file),
        str(second_file),
    ]


def test_normalise_base_url_adds_https_and_strips_api():
    from ae_uploader.client import normalise_base_url

    assert normalise_base_url("data-dev.ae.ic.ac.uk") == "https://data-dev.ae.ic.ac.uk"
    assert normalise_base_url(" https://example.org/api/ ") == "https://example.org"
    assert normalise_base_url("http://localhost:5000/") == "http://localhost:5000"


def test_normalise_base_url_rejects_bad_input():
    import pytest
    from ae_uploader.client import normalise_base_url

    with pytest.raises(ValueError):
        normalise_base_url("   ")
    with pytest.raises(ValueError):
        normalise_base_url("ftp://example.org")


def test_test_connection_records_error_reason():
    from ae_uploader.client import InvenioClient

    client = InvenioClient("not-a-url", "token")
    assert client.test_connection() is False
    assert "No scheme supplied" in client.last_connection_error


def test_upload_file_reports_bytes_and_keeps_content_length(tmp_path: Path):
    from ae_uploader.client import _ProgressReader

    client = InvenioClient("https://example.org", "token")
    data_file = tmp_path / "big.h5"
    data_file.write_bytes(b"z" * 100_000)

    init_response = Mock()
    init_response.raise_for_status = Mock()
    init_response.json.return_value = {
        "entries": [{"key": "big.h5", "links": {"content": "/content"}}]
    }
    upload_response = Mock()
    upload_response.raise_for_status = Mock()
    upload_response.content = b""

    sent = {}

    def fake_put(_url, data=None, **_kwargs):
        assert isinstance(data, _ProgressReader)
        sent["length"] = len(data)
        body = b""
        while True:
            chunk = data.read(8192)
            if not chunk:
                break
            body += chunk
        sent["body"] = body
        return upload_response

    client._draft_resource = Mock(return_value={"id": "d", "links": {}})
    client.session.post = Mock(return_value=init_response)
    client.session.put = fake_put
    progress = []

    client.upload_file("d", str(data_file), bytes_callback=lambda n, total: progress.append((n, total)))

    assert sent["length"] == 100_000
    assert sent["body"] == b"z" * 100_000
    assert sum(n for n, _ in progress) == 100_000
    assert {total for _, total in progress} == {100_000}
