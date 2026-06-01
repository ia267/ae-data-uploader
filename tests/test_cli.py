from __future__ import annotations

import json
from pathlib import Path

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


def test_upload_publish_without_community_requires_force(tmp_path):
    data_file = tmp_path / "data.h5"
    data_file.write_text("dummy", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "upload",
            str(data_file),
            "--publish",
            "--community",
            "",
            "--url",
            "https://example.org",
            "--token",
            "token",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing direct publish without a configured community" in result.output
    assert "--force-direct-publish" in result.output


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
