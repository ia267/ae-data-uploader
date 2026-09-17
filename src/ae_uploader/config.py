"""User-level configuration and credential storage for ae-upload."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import DEFAULT_COMMUNITY, parse_community_list


APP_NAME = "ae-upload"
KEYRING_SERVICE = "ae-upload"
CONFIG_ENVVAR = "AE_UPLOAD_CONFIG_DIR"


@dataclass(frozen=True)
class CredentialStorageResult:
    """Describe where a token was stored."""

    method: str
    path: Optional[Path] = None
    warning: Optional[str] = None


def user_config_dir() -> Path:
    """Return the user-specific config directory for Linux, macOS, and Windows."""
    override = os.environ.get(CONFIG_ENVVAR)
    if override:
        return Path(override).expanduser()

    try:
        from platformdirs import user_config_dir as platform_user_config_dir
    except ImportError:
        return Path.home() / ".config" / APP_NAME

    try:
        return Path(platform_user_config_dir(APP_NAME, appauthor=False))
    except TypeError:
        return Path(platform_user_config_dir(APP_NAME))


def user_config_path() -> Path:
    """Return the path to the non-secret user configuration file."""
    return user_config_dir() / "config.json"


def fallback_credentials_path() -> Path:
    """Return the path to the protected fallback credentials file."""
    return user_config_dir() / "credentials.json"


def _secure_chmod(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Windows does not fully support POSIX modes. The file still lives under
        # the user's profile-specific config directory.
        pass


def _secure_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    _secure_chmod(tmp_path)
    os.replace(tmp_path, path)
    _secure_chmod(path)


def _normalise_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise config from current JSON keys or env-style keys."""
    url = (data.get("url") or data.get("INVENIO_URL") or "").strip()
    namespace = (
        data.get("namespace")
        or data.get("CUSTOM_FIELD_NAMESPACE")
        or "domain"
    ).strip()
    community = (
        data.get("community")
        or data.get("INVENIO_COMMUNITY")
        or DEFAULT_COMMUNITY
    ).strip()

    allowed = data.get("allowed_communities")
    if isinstance(allowed, list):
        allowed_communities = parse_community_list(",".join(str(item) for item in allowed))
    else:
        allowed_communities = parse_community_list(
            str(allowed or data.get("INVENIO_COMMUNITIES") or "")
        )
    if not allowed_communities and community:
        allowed_communities = [community]

    return {
        "url": url,
        "namespace": namespace,
        "community": community,
        "allowed_communities": allowed_communities,
    }


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load non-secret user configuration."""
    config_path = path or user_config_path()
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return _normalise_config(data)


def save_config(
    url: str,
    namespace: str = "domain",
    community: str = DEFAULT_COMMUNITY,
    allowed_communities: Optional[List[str]] = None,
    path: Optional[Path] = None,
) -> Path:
    """Save non-secret user configuration."""
    communities = parse_community_list(",".join(allowed_communities or []))
    if community and community not in communities:
        communities.insert(0, community)

    config_path = path or user_config_path()
    _secure_write_json(
        config_path,
        {
            "url": url,
            "namespace": namespace,
            "community": community,
            "allowed_communities": communities,
        },
    )
    return config_path


def _get_keyring_token(url: str) -> Optional[str]:
    try:
        import keyring
    except ImportError:
        return None

    try:
        token = keyring.get_password(KEYRING_SERVICE, url)
    except Exception:
        return None
    return token or None


def _keyring_backend_is_secure(backend: Any) -> bool:
    """
    Return False for keyring backends that do not protect the secret.

    ``keyring`` can silently select the ``fail`` backend (nothing available),
    a ``null`` backend, or plaintext/obfuscated file backends from
    ``keyrings.alt``. Only real system credential stores count as secure.
    """
    backends = getattr(backend, "backends", None) or [backend]
    for candidate in backends:
        module = type(candidate).__module__
        if module.startswith("keyrings.alt") or module in (
            "keyring.backends.fail",
            "keyring.backends.null",
        ):
            continue
        return True
    return False


def _save_keyring_token(url: str, token: str) -> bool:
    try:
        import keyring
    except ImportError:
        return False

    try:
        if not _keyring_backend_is_secure(keyring.get_keyring()):
            return False
        keyring.set_password(KEYRING_SERVICE, url, token)
    except Exception:
        return False
    return True


def _load_fallback_tokens(path: Optional[Path] = None) -> Dict[str, str]:
    credentials_path = path or fallback_credentials_path()
    if not credentials_path.exists():
        return {}

    with open(credentials_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tokens = data.get("tokens", {}) if isinstance(data, dict) else {}
    if not isinstance(tokens, dict):
        return {}
    return {str(key): str(value) for key, value in tokens.items() if value}


def load_token(url: str) -> Optional[str]:
    """Load a token from keyring, falling back to the protected credentials file."""
    url = url.strip()
    if not url:
        return None

    token = _get_keyring_token(url)
    if token:
        return token

    return _load_fallback_tokens().get(url)


def _delete_keyring_token(url: str) -> bool:
    try:
        import keyring
    except ImportError:
        return False

    try:
        if not keyring.get_password(KEYRING_SERVICE, url):
            return False
        keyring.delete_password(KEYRING_SERVICE, url)
    except Exception:
        return False
    return True


def delete_token(*urls: str) -> List[str]:
    """
    Delete saved tokens for the given URLs from every local store.

    Returns a description of each place a token was removed from. The token
    is not revoked on the server; that has to be done in the Invenio UI.
    """
    keys = []
    for url in urls:
        url = (url or "").strip()
        if url and url not in keys:
            keys.append(url)

    removed: List[str] = []
    if any([_delete_keyring_token(url) for url in keys]):
        removed.append("system credential store")

    credentials_path = fallback_credentials_path()
    tokens = _load_fallback_tokens(credentials_path)
    remaining = {key: value for key, value in tokens.items() if key not in keys}
    if len(remaining) != len(tokens):
        if remaining:
            _secure_write_json(credentials_path, {"tokens": remaining})
        else:
            credentials_path.unlink()
        removed.append(str(credentials_path))
    return removed


def save_token(
    url: str, token: str, allow_file: bool = False
) -> CredentialStorageResult:
    """
    Save a token to the system credential store.

    If no secure credential store is available the token is not saved
    (``method="none"``), unless ``allow_file`` is True, in which case it is
    written to a protected user-level file.
    """
    url = url.strip()
    if _save_keyring_token(url, token):
        return CredentialStorageResult(method="keyring")

    if not allow_file:
        return CredentialStorageResult(
            method="none",
            warning=(
                "No system credential store is available, so the token was not saved."
            ),
        )

    credentials_path = fallback_credentials_path()
    tokens = _load_fallback_tokens(credentials_path)
    tokens[url] = token
    _secure_write_json(credentials_path, {"tokens": tokens})
    return CredentialStorageResult(
        method="file",
        path=credentials_path,
        warning=(
            "System credential store was unavailable; token saved in a file "
            "readable only by your user account."
        ),
    )
