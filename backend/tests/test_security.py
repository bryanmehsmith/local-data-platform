import pytest
from fastapi import HTTPException

from app.config import settings
from app.security import hash_api_key, require_api_key


def _set_hashes(monkeypatch, *plaintext_keys):
    monkeypatch.setattr(settings, "api_key", "")
    monkeypatch.setattr(
        settings,
        "backend_api_key_hashes_raw",
        ",".join(hash_api_key(k) for k in plaintext_keys),
    )


def test_valid_key_passes(monkeypatch):
    _set_hashes(monkeypatch, "correct-key")
    require_api_key(x_api_key="correct-key")


def test_missing_key_raises_401(monkeypatch):
    _set_hashes(monkeypatch, "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="")
    assert exc_info.value.status_code == 401


def test_wrong_key_raises_401(monkeypatch):
    _set_hashes(monkeypatch, "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="wrong-key")
    assert exc_info.value.status_code == 401


def test_legacy_plaintext_key_still_works_when_no_hashes_configured(monkeypatch):
    monkeypatch.setattr(settings, "backend_api_key_hashes_raw", "")
    monkeypatch.setattr(settings, "api_key", "correct-key")
    require_api_key(x_api_key="correct-key")


def test_rotation_old_and_new_hash_both_accepted_then_old_rejected(monkeypatch):
    old_hash = hash_api_key("old-key")
    new_hash = hash_api_key("new-key")

    monkeypatch.setattr(settings, "api_key", "")
    monkeypatch.setattr(settings, "backend_api_key_hashes_raw", f"{old_hash},{new_hash}")
    require_api_key(x_api_key="old-key")
    require_api_key(x_api_key="new-key")

    # Rotate: drop the old hash from the configured list.
    monkeypatch.setattr(settings, "backend_api_key_hashes_raw", new_hash)
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="old-key")
    assert exc_info.value.status_code == 401
    require_api_key(x_api_key="new-key")
