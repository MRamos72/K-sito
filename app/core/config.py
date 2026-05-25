"""
Configuración centralizada del proyecto.
Lee variables del archivo .env.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global cargada desde el archivo .env."""

    # ===== API =====
    app_name: str = "K-Sito Assistant"
    app_version: str = "2.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5010

    # ===== Anthropic Claude =====
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-5"
    claude_max_tokens: int = 1024

    # ===== RAG / FAISS =====
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = 500
    chunk_overlap: int = 80
    top_k_results: int = 4

    # ===== Paths =====
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    docs_dir: Path = Path("docs")
    index_dir: Path = Path("backend/data/faiss_index")
    frontend_dir: Path = Path("frontend")

    # ===== CORS =====
    # ⚠ FastAPI CORSMiddleware NO soporta wildcards en `allow_origins`.
    # Para `*.viveenlabaja.mx` se usa el regex de abajo (`allowed_origin_regex`).
    # Aquí dejamos los orígenes EXACTOS — incluye localhost para dev.
    allowed_origins: list[str] = [
        "http://localhost:5010",
        "http://127.0.0.1:5010",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://experience.viveenlabaja.mx",
        "https://viveenlabaja.mx",
    ]
    # Regex que SÍ acepta wildcards de subdominio
    allowed_origin_regex: str = r"https://([a-z0-9-]+\.)*viveenlabaja\.mx"

    # ===== Site identity =====
    assistant_name: str = "K-Sito"
    site_name: str = "Vive en la Baja"
    contact_whatsapp: str = "664 912 0331"
    contact_email: str = "cobranza@vivelabaja.com"

    # ===== Rate limiting =====
    rate_limit_per_minute: int = 15

    # ===== Session =====
    session_history_max: int = 20
    session_ttl_hours: int = 2

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def absolute_docs_dir(self) -> Path:
        return self.base_dir / self.docs_dir

    @property
    def absolute_index_dir(self) -> Path:
        return self.base_dir / self.index_dir


# Singleton — se importa desde cualquier parte del proyecto
settings = Settings()
