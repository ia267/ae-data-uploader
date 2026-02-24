from __future__ import annotations

import json

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
    runner = CliRunner()

    result = runner.invoke(cli, ["info"])

    assert result.exit_code == 0
    assert "[OK] Configuration looks good!" in result.output


def test_save_credentials_writes_secure_env_file(tmp_path):
    env_path = tmp_path / ".env"

    _save_credentials(env_path, "https://example.org", "token", "domain")

    env_contents = env_path.read_text(encoding="utf-8")
    assert "INVENIO_URL=https://example.org" in env_contents
    assert "INVENIO_TOKEN=token" in env_contents
    assert "CUSTOM_FIELD_NAMESPACE=domain" in env_contents
    assert env_path.stat().st_mode & 0o777 == 0o600
