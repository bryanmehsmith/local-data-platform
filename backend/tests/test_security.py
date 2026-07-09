import pytest
from fastapi import HTTPException

from app.config import settings
from app.security import require_api_key


def test_valid_key_passes(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "correct-key")
    require_api_key(x_api_key="correct-key")


def test_missing_key_raises_401(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="")
    assert exc_info.value.status_code == 401


def test_wrong_key_raises_401(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="wrong-key")
    assert exc_info.value.status_code == 401
