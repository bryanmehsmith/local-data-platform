from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.plugin_loader import load_plugin_routers
from app.routers import chat, dagster, health, search, services, trino
from app.security import require_api_key

app = FastAPI(title="Local Data Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(trino.router, prefix="/api/trino", dependencies=[Depends(require_api_key)])
app.include_router(dagster.router, prefix="/api/dagster", dependencies=[Depends(require_api_key)])
app.include_router(chat.router, prefix="/api/chat", dependencies=[Depends(require_api_key)])
app.include_router(search.router, prefix="/api/search", dependencies=[Depends(require_api_key)])
app.include_router(services.router, prefix="/api/services", dependencies=[Depends(require_api_key)])

load_plugin_routers(app, settings.backend_plugin_dirs)
