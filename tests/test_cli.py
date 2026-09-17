from __future__ import annotations

import json
from pathlib import Path

import requests
from click.testing import CliRunner

from ae_uploader.cli import cli
from ae_uploader.config import CredentialStorageResult, load_config, save_config


def _set_test_config_dir(monkeypatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "ae-upload-config"
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(config_dir))
    return config_dir


def test_generate_command_creates_template_file(tmp_path):
    output_file = tmp_path / "metadata.json"
    runner = CliRunner()

    result = runner.invoke(cli, ["generate", "numerical", "--output", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()
    metadata = json.loads(output_file.read_text(encoding="utf-8"))
    assert metadata["domain"]["observations"][0]["observation_type"] == "numerical"
    assert "identifiers" not in metadata["creators"][0]["person_or_org"]


def test_validate_command_accepts_valid_metadata(tmp_path, valid_metadata: dict):
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(valid_metadata), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(cli, ["validate", str(metadata_file)])

    assert result.exit_code == 0
    assert "[OK] Metadata is valid!" in result.output


def test_validate_command_fails_for_invalid_metadata(tmp_path, valid_metadata: dict):
    valid_metadata.pop("title")
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(valid_metadata), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(cli, ["validate", str(metadata_file)])

    assert result.exit_code == 1
    assert "[FAILED] Validation failed:" in result.output


def test_generate_index_command_creates_csv_index(tmp_path):
    data_file = tmp_path / "data.csv"
    index_file = tmp_path / "data_index.json"
    data_file.write_text("a,b\n1,2\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["generate-index", str(data_file), "--output", str(index_file)],
    )

    assert result.exit_code == 0
    assert index_file.exists()
    generated_index = json.loads(index_file.read_text(encoding="utf-8"))
    assert generated_index["file_type"] == "csv"


def test_info_command_reports_ready_configuration(monkeypatch):
    monkeypatch.setenv("INVENIO_URL", "https://example.org")
    monkeypatch.setenv("INVENIO_TOKEN", "token")
    monkeypatch.setenv("INVENIO_COMMUNITIES", "ae-dept-data,future-lab-data")
    runner = CliRunner()

    result = runner.invoke(cli, ["info"])

    assert result.exit_code == 0
    assert "[OK] Configuration looks good!" in result.output
    assert "INVENIO_COMMUNITIES: ae-dept-data, future-lab-data" in result.output


def test_configure_command_shows_export_form_next_steps(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummyResponse:
        status_code = 200

    class _DummySession:
        def __init__(self):
            self.verify = True

        def get(self, _url):
            return _DummyResponse()

    class _DummyClient:
        def __init__(self, url, token, namespace, community, allowed_communities=None):
            self.base_url = url
            self.token = token
            self.namespace = namespace
            self.community = community
            self.allowed_communities = allowed_communities or []
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr(
        "ae_uploader.cli.save_token",
        lambda _url, _token, **_kwargs: CredentialStorageResult(
            method="file",
            path=config_dir / "credentials.json",
        ),
    )
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\nn\n",
        )

    assert result.exit_code == 0
    assert "For each new dataset:" in result.output
    assert "ae-upload export-form --output metadata_form.html" in result.output
    assert "save it inside ./my_data_directory" in result.output
    assert "alternative: ae-upload generate numerical" not in result.output
    assert "ae-upload validate metadata.json" not in result.output
    assert "ae-upload upload ./my_data_directory" in result.output
    assert "Configuration saved to" in result.output
    assert "Token saved to" in result.output
    assert "For scripts or temporary credentials" in result.output
    assert "INVENIO_TOKEN=... ae-upload upload ./data" in result.output
    assert "Custom Field Namespace" not in result.output
    assert "Enter namespace" not in result.output


def test_configure_uses_default_community_without_advanced_prompt(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummyResponse:
        status_code = 200

    class _DummySession:
        def __init__(self):
            self.verify = True

        def get(self, _url):
            return _DummyResponse()

    class _DummyClient:
        def __init__(self, url, token, namespace, community, allowed_communities=None):
            self.base_url = url
            self.token = token
            self.namespace = namespace
            self.community = community
            self.allowed_communities = allowed_communities or []
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr(
        "ae_uploader.cli.save_token",
        lambda _url, _token, **_kwargs: CredentialStorageResult(
            method="file",
            path=config_dir / "credentials.json",
        ),
    )
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\nn\n",
        )

    assert result.exit_code == 0
    config = load_config()
    assert config["url"] == "https://example.org"
    assert config["namespace"] == "domain"
    assert config["community"] == "ae-dept-data"
    assert config["allowed_communities"] == ["ae-dept-data"]


def test_configure_can_set_advanced_communities(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummyResponse:
        status_code = 200

    class _DummySession:
        def __init__(self):
            self.verify = True

        def get(self, _url):
            return _DummyResponse()

    class _DummyClient:
        def __init__(self, url, token, namespace, community, allowed_communities=None):
            self.base_url = url
            self.token = token
            self.namespace = namespace
            self.community = community
            self.allowed_communities = allowed_communities or []
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr(
        "ae_uploader.cli.save_token",
        lambda _url, _token, **_kwargs: CredentialStorageResult(
            method="file",
            path=config_dir / "credentials.json",
        ),
    )
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\ny\nfuture-lab-data\nae-dept-data\n",
        )

    assert result.exit_code == 0
    config = load_config()
    assert config["community"] == "future-lab-data"
    assert config["allowed_communities"] == ["future-lab-data", "ae-dept-data"]


def test_upload_submit_review_without_community_is_rejected(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--submit-review",
            "--community",
            "",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 1
    assert "Cannot submit for review without a configured community" in result.output
    assert "Direct publish without review is disabled" in result.output


def test_upload_rejects_force_direct_publish_flag(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--force-direct-publish",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert "--force-direct-publish" in result.output


def test_upload_rejects_conflicting_draft_and_submit_review_flags(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--draft-only",
            "--submit-review",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 1
    assert "Choose either --draft-only or --submit-review" in result.output


def test_upload_rejects_unapproved_community_before_creating_draft(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(valid_metadata), encoding="utf-8")

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            raise ValueError(
                f"Community '{community}' is not in the configured allowlist: "
                "ae-dept-data"
            )

        def create_draft(self, _metadata):
            raise AssertionError("create_draft should not be reached")

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setenv("INVENIO_COMMUNITY", "ae-dept-data")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--community",
            "other-community",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid target community" in result.output
    assert "configured allowlist" in result.output


def test_upload_draft_403_shows_env_file_and_token_hints(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(valid_metadata), encoding="utf-8")

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            response = requests.Response()
            response.status_code = 403
            response.url = "https://example.org/api/records"
            response._content = b'{"message": "Forbidden"}'
            raise requests.exceptions.HTTPError(
                "403 Client Error: FORBIDDEN",
                response=response,
            )

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 1
    assert "Error creating draft" in result.output
    assert "Forbidden" in result.output
    assert "ae-upload configure" in result.output
    assert "INVENIO_TOKEN" in result.output
    assert "/account/settings/applications/tokens/new/" in result.output


def test_upload_loads_user_config_without_env_file(
    tmp_path, valid_metadata: dict, monkeypatch
):
    _set_test_config_dir(monkeypatch, tmp_path)
    for name in [
        "INVENIO_URL",
        "INVENIO_TOKEN",
        "CUSTOM_FIELD_NAMESPACE",
        "INVENIO_COMMUNITY",
        "INVENIO_COMMUNITIES",
    ]:
        monkeypatch.delenv(name, raising=False)

    save_config(
        "https://stored.example.org",
        namespace="domain",
        community="ae-dept-data",
        allowed_communities=["ae-dept-data"],
    )
    monkeypatch.setattr("ae_uploader.cli.load_token", lambda _url: "stored-token")

    captured = {}

    class _DummyClient:
        def __init__(self, url, token, namespace, community, allowed_communities=None):
            captured["url"] = url
            captured["token"] = token
            captured["namespace"] = namespace
            captured["community"] = community
            captured["allowed_communities"] = allowed_communities
            self.session = type("Session", (), {"verify": True})()

        @staticmethod
        def uploadable_files(directory):
            return [Path(directory) / "data.h5"]

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            return {"id": "draft-1"}

        def upload_directory(
            self, _draft_id, _directory, create_zip=True, progress_callback=None
        ):
            return [{"key": "data.h5"}]

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    with runner.isolated_filesystem():
        data_dir = Path("dataset")
        data_dir.mkdir()
        (data_dir / "metadata.json").write_text(
            json.dumps(valid_metadata),
            encoding="utf-8",
        )
        (data_dir / "data.h5").write_text("dummy", encoding="utf-8")

        result = runner.invoke(cli, ["upload", str(data_dir)])

    assert result.exit_code == 0
    assert captured["url"] == "https://stored.example.org"
    assert captured["token"] == "stored-token"
    assert captured["community"] == "ae-dept-data"
    assert captured["allowed_communities"] == ["ae-dept-data"]


def test_upload_directory_reports_individual_file_progress(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_dir = tmp_path / "dataset"
    nested_dir = data_dir / "nested"
    nested_dir.mkdir(parents=True)
    (data_dir / "metadata.json").write_text(json.dumps(valid_metadata), encoding="utf-8")
    first_file = data_dir / "a.h5"
    second_file = nested_dir / "b.csv"
    first_file.write_text("a", encoding="utf-8")
    second_file.write_text("b", encoding="utf-8")

    upload_args = {}

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        @staticmethod
        def uploadable_files(directory):
            return [first_file, second_file]

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            return {"id": "draft-1"}

        def upload_directory(
            self, _draft_id, directory, create_zip=True, progress_callback=None
        ):
            upload_args["directory"] = directory
            upload_args["create_zip"] = create_zip
            files = self.uploadable_files(directory)
            for index, file_path in enumerate(files, start=1):
                progress_callback(file_path, index, len(files))
            return [{"key": file_path.name} for file_path in files]

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_dir),
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 0
    assert upload_args == {"directory": str(data_dir), "create_zip": False}
    assert "[INFO] Uploadable files: 2" in result.output
    assert "[INFO] Upload mode: individual files" in result.output
    assert "[1/2] Uploading a.h5" in result.output
    assert "[2/2] Uploading nested/b.csv as b.csv" in result.output


def test_upload_directory_zip_mode_uses_archive_upload(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_dir = tmp_path / "dataset"
    data_dir.mkdir()
    (data_dir / "metadata.json").write_text(json.dumps(valid_metadata), encoding="utf-8")
    data_file = data_dir / "a.h5"
    data_file.write_text("a", encoding="utf-8")

    upload_args = {}

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        @staticmethod
        def uploadable_files(_directory):
            return [data_file]

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            return {"id": "draft-2"}

        def upload_directory(
            self, _draft_id, _directory, create_zip=True, progress_callback=None
        ):
            upload_args["create_zip"] = create_zip
            upload_args["progress_callback"] = progress_callback
            return [{"key": "dataset.zip"}]

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_dir),
            "--zip",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 0
    assert upload_args == {"create_zip": True, "progress_callback": None}
    assert "[INFO] Upload mode: single zip archive" in result.output
    assert "[INFO] Creating zip archive before upload..." in result.output
    assert "[OK] Uploaded 1 archive" in result.output


def test_upload_draft_preselects_community_when_configured(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_dir = tmp_path / "dataset"
    data_dir.mkdir()
    (data_dir / "metadata.json").write_text(json.dumps(valid_metadata), encoding="utf-8")
    (data_dir / "a.h5").write_text("a", encoding="utf-8")

    calls = {"set_draft_submission_community": []}

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        @staticmethod
        def uploadable_files(_directory):
            return [data_dir / "a.h5"]

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            return {"id": "draft-7"}

        def upload_directory(
            self, _draft_id, _directory, create_zip=True, progress_callback=None
        ):
            return [{"key": "a.h5"}]

        def set_draft_submission_community(self, draft_id, community_id=None):
            calls["set_draft_submission_community"].append((draft_id, community_id))
            return {"id": "review-draft-1"}

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_dir),
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 0
    assert calls["set_draft_submission_community"] == [("draft-7", "ae-dept-data")]
    assert "[INFO] Setting draft community..." in result.output
    assert "[OK] Draft linked to community: ae-dept-data" in result.output


def test_upload_submit_review_submits_draft_for_community_review(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_dir = tmp_path / "dataset"
    data_dir.mkdir()
    (data_dir / "metadata.json").write_text(json.dumps(valid_metadata), encoding="utf-8")
    (data_dir / "a.h5").write_text("a", encoding="utf-8")

    calls = {"submit_draft_for_review": [], "set_draft_submission_community": []}

    class _DummyClient:
        def __init__(self, *_args, **_kwargs):
            self.session = type("Session", (), {"verify": True})()

        @staticmethod
        def uploadable_files(_directory):
            return [data_dir / "a.h5"]

        def test_connection(self):
            return True

        def resolve_submission_community(self, community):
            return community

        def create_draft(self, _metadata):
            return {"id": "draft-8"}

        def upload_directory(
            self, _draft_id, _directory, create_zip=True, progress_callback=None
        ):
            return [{"key": "a.h5"}]

        def set_draft_submission_community(self, draft_id, community_id=None):
            calls["set_draft_submission_community"].append((draft_id, community_id))
            return {"id": "review-draft-2"}

        def submit_draft_for_review(self, draft_id, community_id=None):
            calls["submit_draft_for_review"].append((draft_id, community_id))
            return {"id": "review-request-1"}

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_dir),
            "--submit-review",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 0
    assert calls["set_draft_submission_community"] == []
    assert calls["submit_draft_for_review"] == [("draft-8", "ae-dept-data")]
    assert "[INFO] Submitting draft for community review..." in result.output
    assert "[OK] Draft submitted for community review!" in result.output
    assert "Request ID: review-request-1" in result.output


def test_upload_rejects_publish_flag(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--publish",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert "--publish" in result.output


def test_upload_rejects_env_file_flag(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("INVENIO_TOKEN=token\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--env-file",
            str(env_file),
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert "--env-file" in result.output


def test_configure_adds_https_to_bare_hostname(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummyResponse:
        status_code = 200

    class _DummySession:
        def __init__(self):
            self.verify = True

        def get(self, _url):
            return _DummyResponse()

    class _DummyClient:
        def __init__(self, url, token, namespace, community, allowed_communities=None):
            self.base_url = url
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr(
        "ae_uploader.cli.save_token",
        lambda _url, _token, **_kwargs: CredentialStorageResult(
            method="file",
            path=config_dir / "credentials.json",
        ),
    )
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["configure"],
        input="data-dev.ae.ic.ac.uk/\nsecret-token\nn\n",
    )

    assert result.exit_code == 0
    assert "secret-token" not in result.output
    assert load_config()["url"] == "https://data-dev.ae.ic.ac.uk"


def test_upload_normalises_url_and_reports_connection_error(
    tmp_path, valid_metadata: dict, monkeypatch
):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(valid_metadata), encoding="utf-8")
    seen = {}

    class _DummyClient:
        def __init__(self, url, *_args, **_kwargs):
            seen["url"] = url
            self.session = type("Session", (), {"verify": True})()
            self.last_connection_error = "Connection refused"

        def test_connection(self):
            return False

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["upload", str(data_file), "--url", "example.org", "--token", "token"],
    )

    assert result.exit_code == 1
    assert seen["url"] == "https://example.org"
    assert "Connection refused" in result.output


def test_configure_without_keyring_does_not_save_token(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummySession:
        verify = True

        def get(self, _url):
            return type("Response", (), {"status_code": 200})()

    class _DummyClient:
        def __init__(self, url, *_args, **_kwargs):
            self.base_url = url
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr("ae_uploader.config._save_keyring_token", lambda _u, _t: False)
    monkeypatch.setattr("ae_uploader.config._get_keyring_token", lambda _u: None)

    result = CliRunner().invoke(
        cli, ["configure"], input="https://example.org\nsecret-token\nn\n"
    )

    assert result.exit_code == 0
    assert "token was not saved" in result.output
    assert "ae-upload configure --token-file" in result.output
    assert not (config_dir / "credentials.json").exists()
    assert load_config()["url"] == "https://example.org"


def test_configure_token_file_flag_saves_token_without_keyring(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummySession:
        verify = True

        def get(self, _url):
            return type("Response", (), {"status_code": 200})()

    class _DummyClient:
        def __init__(self, url, *_args, **_kwargs):
            self.base_url = url
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr("ae_uploader.config._save_keyring_token", lambda _u, _t: False)
    monkeypatch.setattr("ae_uploader.config._get_keyring_token", lambda _u: None)

    result = CliRunner().invoke(
        cli,
        ["configure", "--token-file"],
        input="https://example.org\nsecret-token\nn\n",
    )

    assert result.exit_code == 0
    assert (config_dir / "credentials.json").exists()
    assert "[WARNING]" in result.output


def test_logout_removes_saved_token_and_explains_revocation(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("INVENIO_URL", raising=False)
    monkeypatch.delenv("INVENIO_TOKEN", raising=False)
    monkeypatch.setattr("ae_uploader.config._save_keyring_token", lambda _u, _t: False)
    monkeypatch.setattr("ae_uploader.config._get_keyring_token", lambda _u: None)
    monkeypatch.setattr("ae_uploader.config._delete_keyring_token", lambda _u: False)
    save_config("https://example.org", "domain", "ae-dept-data", ["ae-dept-data"])
    from ae_uploader import config

    config.save_token("https://example.org", "secret-token", allow_file=True)
    config.save_token("https://other.org", "other-token", allow_file=True)

    result = CliRunner().invoke(cli, ["logout"])

    assert result.exit_code == 0
    assert "Removed saved token" in result.output
    assert "https://example.org/account/settings/applications/" in result.output
    assert config.load_token("https://example.org") is None
    assert config.load_token("https://other.org") == "other-token"
    assert load_config()["url"] == "https://example.org"


def test_logout_without_saved_token(tmp_path, monkeypatch):
    _set_test_config_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("INVENIO_URL", raising=False)
    monkeypatch.setenv("INVENIO_TOKEN", "env-token")
    monkeypatch.setattr("ae_uploader.config._delete_keyring_token", lambda _u: False)

    result = CliRunner().invoke(cli, ["logout", "--url", "example.org"])

    assert result.exit_code == 0
    assert "No saved token found for https://example.org" in result.output
    assert "INVENIO_TOKEN is set" in result.output


def test_logout_requires_url(tmp_path, monkeypatch):
    _set_test_config_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("INVENIO_URL", raising=False)

    result = CliRunner().invoke(cli, ["logout"])

    assert result.exit_code == 1
    assert "No Invenio URL configured" in result.output


def test_configure_defaults_to_dev_url(tmp_path, monkeypatch):
    config_dir = _set_test_config_dir(monkeypatch, tmp_path)

    class _DummySession:
        verify = True

        def get(self, _url):
            return type("Response", (), {"status_code": 200})()

    class _DummyClient:
        def __init__(self, url, *_args, **_kwargs):
            self.base_url = url
            self.session = _DummySession()

    monkeypatch.setattr("ae_uploader.cli.InvenioClient", _DummyClient)
    monkeypatch.setattr(
        "ae_uploader.cli.save_token",
        lambda _url, _token, **_kwargs: CredentialStorageResult(
            method="file",
            path=config_dir / "credentials.json",
        ),
    )

    result = CliRunner().invoke(cli, ["configure"], input="\nsecret-token\nn\n")

    assert result.exit_code == 0
    assert "[https://data-dev.ae.ic.ac.uk]" in result.output
    assert load_config()["url"] == "https://data-dev.ae.ic.ac.uk"
