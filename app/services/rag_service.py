"""
Servicio RAG: indexa los PDFs de /docs y permite búsqueda semántica con FAISS.

Pipeline:
1. Lee PDFs de /docs con pdfplumber
2. Divide texto en chunks
3. Genera embeddings con sentence-transformers (multilingüe)
4. Construye índice FAISS y lo guarda en disco
5. En tiempo de consulta: encuentra los top-K chunks más relevantes
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
import pdfplumber
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logger import logger


@dataclass
class Chunk:
    """Un fragmento de texto indexado."""
    text: str
    source: str        # nombre del PDF
    page: int          # número de página
    chunk_id: int      # id incremental dentro del documento


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class RAGService:
    """Servicio único de RAG (singleton)."""

    INDEX_FILE = "faiss.index"
    META_FILE = "metadata.pkl"
    INFO_FILE = "info.json"

    def __init__(self) -> None:
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.chunks: List[Chunk] = []
        self.index_dir: Path = settings.absolute_index_dir
        self.docs_dir: Path = settings.absolute_docs_dir

    # ============ EMBEDDING MODEL ============

    def _load_embedding_model(self) -> SentenceTransformer:
        if self.model is None:
            logger.info(f"Cargando modelo de embeddings: {settings.embedding_model}")
            self.model = SentenceTransformer(settings.embedding_model)
        return self.model

    # ============ EXTRACCIÓN DE PDFS ============

    def _extract_pdf_chunks(self, pdf_path: Path) -> List[Chunk]:
        """Extrae texto de un PDF y lo divide en chunks por párrafos."""
        chunks: List[Chunk] = []
        chunk_id = 0
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    if not text.strip():
                        continue
                    # Dividir en chunks con overlap
                    for chunk_text in self._split_into_chunks(text):
                        if len(chunk_text.strip()) < 30:
                            continue
                        chunks.append(Chunk(
                            text=chunk_text.strip(),
                            source=pdf_path.name,
                            page=page_num,
                            chunk_id=chunk_id,
                        ))
                        chunk_id += 1
        except Exception as e:
            logger.error(f"Error procesando {pdf_path.name}: {e}")
        return chunks

    def _clean_text(self, text: str) -> str:
        """Normaliza saltos de línea y espacios."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Une líneas cortas que son parte de un párrafo
        lines = [line.strip() for line in text.split("\n")]
        return " ".join(line for line in lines if line)

    def _split_into_chunks(self, text: str) -> List[str]:
        """Divide texto en chunks con overlap. Sliding window por palabras."""
        words = text.split()
        if len(words) <= settings.chunk_size:
            return [" ".join(words)] if words else []

        chunks = []
        step = max(1, settings.chunk_size - settings.chunk_overlap)
        for i in range(0, len(words), step):
            chunk = words[i:i + settings.chunk_size]
            if chunk:
                chunks.append(" ".join(chunk))
            if i + settings.chunk_size >= len(words):
                break
        return chunks

    # ============ INDEXACIÓN ============

    def build_index(self) -> dict:
        """Lee todos los PDFs de /docs y construye el índice FAISS."""
        if not self.docs_dir.exists():
            logger.warning(f"Carpeta de docs no existe: {self.docs_dir}")
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            return {"chunks": 0, "documents": 0, "error": "no_docs_folder"}

        pdf_files = sorted(self.docs_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No hay PDFs en {self.docs_dir}")
            return {"chunks": 0, "documents": 0, "error": "no_pdfs"}

        logger.info(f"Procesando {len(pdf_files)} PDFs…")
        all_chunks: List[Chunk] = []
        for pdf in pdf_files:
            logger.info(f"  ⤷ {pdf.name}")
            chunks = self._extract_pdf_chunks(pdf)
            all_chunks.extend(chunks)
            logger.info(f"     → {len(chunks)} chunks")

        if not all_chunks:
            return {"chunks": 0, "documents": len(pdf_files), "error": "no_text_extracted"}

        # Generar embeddings
        model = self._load_embedding_model()
        texts = [c.text for c in all_chunks]
        logger.info(f"Generando embeddings para {len(texts)} chunks…")
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        # Construir índice FAISS (Inner Product = similitud coseno con embeddings normalizados)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        # Persistir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_dir / self.INDEX_FILE))
        with open(self.index_dir / self.META_FILE, "wb") as f:
            pickle.dump([asdict(c) for c in all_chunks], f)

        info = {
            "chunks": len(all_chunks),
            "documents": len(pdf_files),
            "dimension": dim,
            "model": settings.embedding_model,
            "doc_names": [p.name for p in pdf_files],
        }
        with open(self.index_dir / self.INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        # Cargar en memoria
        self.index = index
        self.chunks = all_chunks
        logger.info(f"✓ Índice construido: {len(all_chunks)} chunks de {len(pdf_files)} PDFs")
        return info

    # ============ CARGA DEL ÍNDICE ============

    def load_index(self) -> bool:
        """Carga el índice FAISS desde disco si existe."""
        index_path = self.index_dir / self.INDEX_FILE
        meta_path = self.index_dir / self.META_FILE

        if not index_path.exists() or not meta_path.exists():
            logger.warning(
                f"No hay índice en {self.index_dir}. "
                "Corre `python scripts/build_index.py` para crearlo."
            )
            return False

        try:
            self.index = faiss.read_index(str(index_path))
            with open(meta_path, "rb") as f:
                raw_chunks = pickle.load(f)
            self.chunks = [Chunk(**c) for c in raw_chunks]
            self._load_embedding_model()
            logger.info(f"✓ Índice cargado: {len(self.chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error cargando índice: {e}")
            return False

    # ============ BÚSQUEDA ============

    def search(self, query: str, k: Optional[int] = None) -> List[SearchResult]:
        """Busca los k chunks más relevantes para la query."""
        if self.index is None or not self.chunks:
            logger.warning("Índice no inicializado. Llama a load_index() primero.")
            return []

        k = k or settings.top_k_results
        model = self._load_embedding_model()
        query_emb = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, indices = self.index.search(query_emb, k)

        results: List[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            results.append(SearchResult(
                chunk=self.chunks[idx],
                score=float(score),
            ))
        return results

    @property
    def is_ready(self) -> bool:
        return self.index is not None and len(self.chunks) > 0


# Singleton
rag_service = RAGService()
