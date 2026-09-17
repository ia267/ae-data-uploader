from __future__ import annotations

from ae_uploader import config


def test_user_config_dir_uses_override(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(config_dir))

    assert config.user_config_dir() == config_dir
    assert config.user_config_path() == config_dir / "config.json"
    assert config.fallback_credentials_path() == config_dir / "credentials.json"


def _no_keyring(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(config, "_save_keyring_token", lambda _url, _token: False)
    monkeypatch.setattr(config, "_get_keyring_token", lambda _url: None)
    return config_dir


def test_save_token_does_not_write_file_without_keyring(tmp_path, monkeypatch):
    config_dir = _no_keyring(monkeypatch, tmp_path)

    result = config.save_token("https://example.org", "secret-token")

    assert result.method == "none"
    assert result.warning
    assert not (config_dir / "credentials.json").exists()
    assert config.load_token("https://example.org") is None


def test_save_token_file_fallback_is_opt_in(tmp_path, monkeypatch):
    config_dir = _no_keyring(monkeypatch, tmp_path)

    result = config.save_token("https://example.org", "secret-token", allow_file=True)

    assert result.method == "file"
    assert result.path == config_dir / "credentials.json"
    assert result.path.stat().st_mode & 0o777 == 0o600
    assert config.load_token("https://example.org") == "secret-token"


def test_keyring_backend_security_check():
    class SecretService:
        pass

    class PlaintextKeyring:
        pass

    class FailKeyring:
        pass

    SecretService.__module__ = "keyring.backends.SecretService"
    PlaintextKeyring.__module__ = "keyrings.alt.file"
    FailKeyring.__module__ = "keyring.backends.fail"

    class Chainer:
        def __init__(self, backends):
            self.backends = backends

    assert config._keyring_backend_is_secure(SecretService())
    assert not config._keyring_backend_is_secure(PlaintextKeyring())
    assert not config._keyring_backend_is_secure(FailKeyring())
    assert not config._keyring_backend_is_secure(Chainer([PlaintextKeyring()]))
    assert config._keyring_backend_is_secure(
        Chainer([PlaintextKeyring(), SecretService()])
    )
