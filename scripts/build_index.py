"""
Script CLI para construir el índice FAISS a partir de los PDFs en /docs.

Uso:
    python scripts/build_index.py
    python scripts/build_index.py --rebuild   # fuerza reconstrucción
"""
import argparse
import sys
from pathlib import Path

# Agregar backend/ al path para importar app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.logger import logger  # noqa: E402
from app.services.rag_service import rag_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el índice FAISS de T-rrenito")
    parser.add_argument("--rebuild", action="store_true", help="Reconstruir aunque ya exista")
    args = parser.parse_args()

    if not args.rebuild:
        if rag_service.load_index():
            logger.info("Ya existe un índice. Usa --rebuild para forzar reconstrucción.")
            return 0

    logger.info("=" * 60)
    logger.info("Construyendo índice FAISS")
    logger.info("=" * 60)

    info = rag_service.build_index()

    logger.info("=" * 60)
    logger.info("Resumen:")
    for k, v in info.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)

    return 0 if info.get("chunks", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
