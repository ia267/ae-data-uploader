from __future__ import annotations

from ae_uploader import config


def test_user_config_dir_uses_override(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(config_dir))

    assert config.user_config_dir() == config_dir
    assert config.user_config_path() == config_dir / "config.json"
    assert config.fallback_credentials_path() == config_dir / "credentials.json"


def test_save_token_falls_back_to_protected_user_config_file(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(config, "_save_keyring_token", lambda _url, _token: False)
    monkeypatch.setattr(config, "_get_keyring_token", lambda _url: None)

    result = config.save_token("https://example.org", "secret-token")

    assert result.method == "file"
    assert result.path == config_dir / "credentials.json"
    assert result.path.stat().st_mode & 0o777 == 0o600
    assert config.load_token("https://example.org") == "secret-token"
