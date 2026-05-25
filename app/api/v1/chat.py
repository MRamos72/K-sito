"""Endpoints de chat: /api/v1/chat/init y /api/v1/chat"""
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.logger import logger
from app.models.schemas import (
    ChatInitRequest,
    ChatInitResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from app.services.claude_service import claude_service
from app.services.rag_service import rag_service
from app.services.session_service import rate_limiter, session_store
from app.services.site_config import get_form_steps, get_greeting, get_suggestions

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.get("/ping", response_model=HealthResponse)
async def ping() -> HealthResponse:
    """Health check del servicio."""
    return HealthResponse(
        status="ok",
        assistant=settings.assistant_name,
        version=settings.app_version,
        docs_indexed=len(rag_service.chunks) if rag_service.is_ready else 0,
    )


@router.post("/chat/init", response_model=ChatInitResponse)
async def chat_init(req: ChatInitRequest) -> ChatInitResponse:
    """Saludo inicial contextual + sugerencias + form steps según la URL."""
    path = (req.page.path if req.page else "/") or "/"
    return ChatInitResponse(
        greeting=get_greeting(path),
        suggestions=get_suggestions(path),
        form_steps=get_form_steps(path),
        session_id=req.session_id,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Mensaje del usuario → respuesta de T-rrenito basada en los PDFs."""
    # Rate limiting
    if not rate_limiter.is_allowed(req.session_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Vas muy rápido, dame un segundito 🌱",
        )

    # Verificar que el RAG esté listo
    if not rag_service.is_ready:
        logger.error("RAG no está listo. ¿Construiste el índice?")
        return ChatResponse(
            reply=(
                "Ay, todavía no tengo mis documentos cargados 🌱 "
                "Mejor contacta directo al WhatsApp <b>664 912 0331</b>."
            ),
        )

    # Obtener historial
    history = session_store.get_history(req.session_id)

    try:
        reply, sources = claude_service.chat(
            history=history,
            user_message=req.message,
            page=req.page,
        )
    except Exception as e:
        logger.exception("Error llamando a Claude")
        return ChatResponse(
            reply=(
                "Ups, se me ensució el pasto con un error 🌱 "
                "¿Puedes repetir tu pregunta? Si sigue fallando, llama al "
                "WhatsApp <b>664 912 0331</b>."
            ),
        )

    # Guardar en historial
    session_store.add_message(req.session_id, "user", req.message)
    session_store.add_message(req.session_id, "assistant", reply)

    return ChatResponse(reply=reply, sources=sources)
