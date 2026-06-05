from __future__ import annotations

import json
from pathlib import Path

import requests
from click.testing import CliRunner

from ae_uploader.cli import _save_credentials, cli


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


def test_configure_command_shows_export_form_next_steps(monkeypatch):
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
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\ndomain\nn\n",
        )

    assert result.exit_code == 0
    assert "For each new dataset:" in result.output
    assert "ae-upload export-form --output metadata_form.html" in result.output
    assert "# open metadata_form.html in your browser and download metadata.json" in result.output
    assert "alternative: ae-upload generate numerical" not in result.output
    assert "ae-upload validate metadata.json" not in result.output
    assert "ae-upload upload ./my_data_directory" in result.output
    assert "To use this .env file from a different directory:" in result.output
    assert "ae-upload upload ./data --env-file" in result.output


def test_configure_uses_default_community_without_advanced_prompt(monkeypatch):
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
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\ndomain\nn\n",
        )

        env_contents = Path(".env").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert f"INVENIO_COMMUNITY=ae-dept-data" in env_contents
    assert "INVENIO_COMMUNITIES=ae-dept-data" in env_contents


def test_configure_can_set_advanced_communities(monkeypatch):
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
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["configure"],
            input="https://example.org\nsecret-token\ndomain\ny\nfuture-lab-data\nae-dept-data\n",
        )

        env_contents = Path(".env").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "INVENIO_COMMUNITY=future-lab-data" in env_contents
    assert "INVENIO_COMMUNITIES=future-lab-data,ae-dept-data" in env_contents


def test_save_credentials_writes_secure_env_file(tmp_path):
    env_path = tmp_path / ".env"

    _save_credentials(
        env_path,
        "https://example.org",
        "token",
        "domain",
        "ae-dept-data",
        ["ae-dept-data", "future-lab-data"],
    )

    env_contents = env_path.read_text(encoding="utf-8")
    assert "INVENIO_URL=https://example.org" in env_contents
    assert "INVENIO_TOKEN=token" in env_contents
    assert "CUSTOM_FIELD_NAMESPACE=domain" in env_contents
    assert "INVENIO_COMMUNITY=ae-dept-data" in env_contents
    assert "INVENIO_COMMUNITIES=ae-dept-data,future-lab-data" in env_contents
    assert env_path.stat().st_mode & 0o777 == 0o600


def test_save_credentials_persists_single_allowed_community(tmp_path):
    env_path = tmp_path / ".env"

    _save_credentials(
        env_path,
        "https://example.org",
        "token",
        "domain",
        "ae-dept-data",
        ["ae-dept-data"],
    )

    env_contents = env_path.read_text(encoding="utf-8")
    assert "INVENIO_COMMUNITY=ae-dept-data" in env_contents
    assert "INVENIO_COMMUNITIES=ae-dept-data" in env_contents


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
    assert "No such option: --force-direct-publish" in result.output


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
    assert ".env" in result.output
    assert "--env-file /path/to/.env" in result.output
    assert "deposit:write" in result.output


def test_upload_loads_env_from_current_working_directory_without_env_file(
    valid_metadata: dict, monkeypatch
):
    for name in [
        "INVENIO_URL",
        "INVENIO_TOKEN",
        "CUSTOM_FIELD_NAMESPACE",
        "INVENIO_COMMUNITY",
        "INVENIO_COMMUNITIES",
    ]:
        monkeypatch.delenv(name, raising=False)

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
        Path(".env").write_text(
            "\n".join(
                [
                    "INVENIO_URL=https://env.example.org",
                    "INVENIO_TOKEN=env-token",
                    "CUSTOM_FIELD_NAMESPACE=domain",
                    "INVENIO_COMMUNITY=ae-dept-data",
                    "INVENIO_COMMUNITIES=ae-dept-data",
                ]
            ),
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["upload", str(data_dir)])

    assert result.exit_code == 0
    assert captured["url"] == "https://env.example.org"
    assert captured["token"] == "env-token"
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
    assert "No such option: --publish" in result.output
