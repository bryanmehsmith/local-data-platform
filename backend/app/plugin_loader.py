import importlib.util
import logging
from pathlib import Path

from fastapi import Depends, FastAPI

from app.security import require_api_key

logger = logging.getLogger(__name__)


def load_plugin_routers(app: FastAPI, plugin_dirs: list[str]) -> None:
    """Mounts any `router: APIRouter` found in *.py files under plugin_dirs.

    Lets scenario-specific code (the workload repo's backend/ folder,
    bind-mounted in) contribute routes without editing core backend/ code.
    Each file is loaded via spec_from_file_location rather than sys.path
    import, so a plugin file can't collide with or shadow a core module of
    the same name. A broken plugin is logged and skipped, not fatal —
    workload code is untrusted relative to the core app's own startup.
    """
    for dir_path in plugin_dirs:
        directory = Path(dir_path)
        if not directory.is_dir():
            continue
        for py_file in sorted(directory.glob("*.py")):
            if py_file.stem.startswith("_"):
                continue
            try:
                _load_plugin_file(app, py_file)
            except Exception:
                logger.exception("Failed to load workload plugin %s", py_file)


def _load_plugin_file(app: FastAPI, py_file: Path) -> None:
    module_name = f"workload_plugin_{py_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    router = getattr(module, "router", None)
    if router is None:
        logger.warning("Workload plugin %s has no module-level `router` — skipped", py_file)
        return

    prefix = getattr(module, "prefix", f"/api/workload/{py_file.stem}")
    tags = getattr(module, "tags", ["workload"])
    require_auth = getattr(module, "require_auth", True)
    dependencies = [Depends(require_api_key)] if require_auth else []

    app.include_router(router, prefix=prefix, tags=tags, dependencies=dependencies)
    logger.info("Loaded workload plugin router from %s at prefix %s", py_file, prefix)
