"""
T-rrenito Assistant — FastAPI app.

Punto de entrada del backend. Levanta:
- Endpoints /api/v1/...
- Sirve el widget JS desde /widget/
- Sirve la imagen de T-rrenito desde /img/
- (Opcional) sirve la página de demo desde /demo/
"""
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import chat
from app.core.config import settings
from app.core.logger import logger
from app.services.rag_service import rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el índice FAISS al arranque."""
    logger.info(f"🌱 Levantando {settings.app_name} v{settings.app_version}")
    if rag_service.load_index():
        logger.info("✓ RAG listo para servir consultas")
    else:
        logger.warning(
            "⚠ RAG no inicializado. "
            "Corre `python scripts/build_index.py` antes de aceptar tráfico real."
        )
    yield
    logger.info("👋 Apagando T-rrenito")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Asistente virtual de Vive en la Baja con RAG sobre los PDFs oficiales.",
    lifespan=lifespan,
)

# ============ CORS ============
# Soporta dos formas:
#   1) Origenes EXACTOS (settings.allowed_origins) — para localhost, dominios fijos.
#   2) Patrón con * (cualquier entrada de allowed_origins que contenga "*") se convierte
#      en regex automáticamente — útil para *.viveenlabaja.mx.
# Si además existe settings.allowed_origin_regex, se concatena al regex.
exact_origins = [o for o in settings.allowed_origins if "*" not in o]
wildcard_origins = [o for o in settings.allowed_origins if "*" in o]

regex_parts = []
if wildcard_origins:
    regex_parts.extend(
        re.escape(o).replace(r"\*", "[a-z0-9-]+") for o in wildcard_origins
    )
extra_regex = getattr(settings, "allowed_origin_regex", None)
if extra_regex:
    regex_parts.append(extra_regex)
origin_regex = "|".join(regex_parts) if regex_parts else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=exact_origins,
    allow_origin_regex=origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=86400,
)
logger.info(
    f"✓ CORS — exact: {exact_origins} · regex: {origin_regex}"
)

# ============ ROUTES ============
app.include_router(chat.router)

# ============ STATIC FILES ============
frontend_dir = settings.base_dir / settings.frontend_dir
if frontend_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(frontend_dir / "js")), name="widget")
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    app.mount("/img", StaticFiles(directory=str(frontend_dir / "img")), name="img")
    logger.info(f"✓ Sirviendo frontend desde {frontend_dir}")


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/demo")


@app.get("/demo")
async def demo():
    """Página de demo que simula el sitio real."""
    from fastapi.responses import FileResponse
    demo_path = settings.base_dir / settings.frontend_dir / "demo.html"
    if demo_path.exists():
        return FileResponse(str(demo_path))
    return {"error": "demo.html no encontrado"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
