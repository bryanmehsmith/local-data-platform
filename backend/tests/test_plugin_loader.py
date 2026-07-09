from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.plugin_loader import load_plugin_routers


def test_valid_plugin_is_mounted(tmp_path):
    (tmp_path / "hello_plugin.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "require_auth = False\n"
        "\n"
        "@router.get('/ping')\n"
        "def ping():\n"
        "    return {'ok': True}\n"
    )

    app = FastAPI()
    load_plugin_routers(app, [str(tmp_path)])

    client = TestClient(app)
    response = client.get("/api/workload/hello_plugin/ping")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_plugin_without_router_is_skipped(tmp_path):
    (tmp_path / "no_router.py").write_text("x = 1\n")

    app = FastAPI()
    load_plugin_routers(app, [str(tmp_path)])  # must not raise

    paths = {route.path for route in app.routes}
    assert not any(p.startswith("/api/workload/no_router") for p in paths)


def test_broken_plugin_is_skipped_not_fatal(tmp_path):
    (tmp_path / "broken.py").write_text("raise RuntimeError('boom')\n")

    app = FastAPI()
    load_plugin_routers(app, [str(tmp_path)])  # must not raise, just logged

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_require_auth_false_needs_no_api_key(tmp_path):
    (tmp_path / "open_plugin.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "require_auth = False\n"
        "\n"
        "@router.get('/open')\n"
        "def open_route():\n"
        "    return {'open': True}\n"
    )

    app = FastAPI()
    load_plugin_routers(app, [str(tmp_path)])

    client = TestClient(app)
    response = client.get("/api/workload/open_plugin/open")
    assert response.status_code == 200


def test_require_auth_true_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")

    (tmp_path / "guarded_plugin.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "\n"
        "@router.get('/secure')\n"
        "def secure_route():\n"
        "    return {'secure': True}\n"
    )

    app = FastAPI()
    load_plugin_routers(app, [str(tmp_path)])

    client = TestClient(app)
    response = client.get("/api/workload/guarded_plugin/secure")
    assert response.status_code == 401

    response = client.get(
        "/api/workload/guarded_plugin/secure", headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 200
