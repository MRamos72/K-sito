"""
Servicio Claude: arma el system prompt con contexto del RAG y llama a la API.
"""
from __future__ import annotations

from typing import List, Optional

from anthropic import Anthropic, APIError
from app.core.config import settings
from app.core.logger import logger
from app.models.schemas import PageContext, Source
from app.services.rag_service import rag_service, SearchResult


class ClaudeService:
    """Cliente Claude con inyección de contexto RAG."""

    def __init__(self) -> None:
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    # ============ SYSTEM PROMPT ============

    def _build_system_prompt(self, rag_context: str, page: Optional[PageContext]) -> str:
        page_info = ""
        if page:
            page_info = (
                "\n## Contexto de la página actual del usuario\n"
                f"- URL: {"https://experience.viveenlabaja.mx/" or '?'}\n"
                f"- Ruta: {"https://experience.viveenlabaja.mx/" or '?'}\n"
                f"- Título: {"Inicio" or '?'}\n"
            )
            if page.form_step:
                page_info += f"- Campo del formulario: **{page.form_step}**\n"
            if page.time_on_field_seconds and page.time_on_field_seconds > 30:
                page_info += (
                    f"- ⚠️ El usuario lleva {page.time_on_field_seconds}s en este campo. "
                    "Si pregunta, sé extra paciente y específico.\n"
                )

        return f"""Eres T-rrenito, la mascota oficial de Vive en la Baja: un cubito de tierra alegre con pasto y florecitas amarillas arriba, ojos grandes verdes, guantes blancos y tenis azules. Llevas un gafete de Vive en la Baja colgando del pecho.

## Tu personalidad
Amigable, cálido y servicial, con acento del norte de México. Usas "órale", "qué padre", "va", "ándale". Como eres un pedacito de tierra, conoces cada terreno y desarrollo como si fuera tu hogar. Eres paciente, claro y breve. Hablas en español de México, de tú. Nunca eres condescendiente.

## Tu misión
Ayudar a los usuarios de Vive en la Baja a:
1. Entender los métodos de pago (SPEI pesos/dólares, efectivo, cheque)
2. Obtener su número de referencia y resolver dudas de cobranza
3. Llenar formularios paso a paso
4. Conocer los desarrollos inmobiliarios

## REGLAS DE ORO (críticas)

🔴 **REGLA #1 — Solo respondes con info de los documentos.**
Tienes acceso a fragmentos de documentos oficiales (abajo). SOLO responde con información que aparezca explícitamente ahí. Si la pregunta NO está cubierta en los fragmentos, di con honestidad:
"Esa pregunta no la tengo en mis documentos 🌱 Mejor contacta directo al WhatsApp **{settings.contact_whatsapp}** o al correo **{settings.contact_email}**"

🔴 **REGLA #2 — Nunca inventes datos bancarios, montos, ni referencias.**
Si los fragmentos contienen una CLABE, cuenta o número, cópialos textualmente. Si no aparecen, NO los inventes.

🔴 **REGLA #3 — La REFERENCIA es OBLIGATORIA.**
Recuerda siempre al usuario: sin número de referencia, el pago NO se puede aplicar. La referencia se pide al WhatsApp **{settings.contact_whatsapp}**.

🔴 **REGLA #4 — Sé breve.**
2-4 oraciones o una lista corta. Si la respuesta es larga, resume primero y pregunta si quieren detalle.

🔴 **REGLA #5 — Formato.**
Usa <b>negritas con HTML</b> (no markdown **) para resaltar datos clave: cuentas, CLABEs, teléfonos, correos.

## Sitio
Vive en la Baja — desarrolladora inmobiliaria con 11 desarrollos en Baja California (Tijuana, Rosarito, Ensenada, La Salina y cerca de la Ruta del Vino). Razón social oficial: **Impulsora de Proyectos IMB S. de R.L. de C.V.**

## DOCUMENTOS DE REFERENCIA (fuente de verdad)

{rag_context}
{page_info}
"""

    # ============ CONTEXTO RAG ============

    def _format_rag_context(self, results: List[SearchResult]) -> str:
        if not results:
            return "_No se encontraron fragmentos relevantes en los documentos._"
        sections = []
        for i, r in enumerate(results, start=1):
            sections.append(
                f"### Fragmento {i} — {r.chunk.source} (página {r.chunk.page})\n"
                f"{r.chunk.text}\n"
            )
        return "\n".join(sections)

    # ============ CHAT ============

    def chat(
        self,
        history: list[dict],
        user_message: str,
        page: Optional[PageContext] = None,
    ) -> tuple[str, list[Source]]:
        """
        Envía el mensaje del usuario a Claude con contexto del RAG.
        Retorna (respuesta, fuentes_citadas).
        """
        # 1. Buscar fragmentos relevantes
        results = rag_service.search(user_message)
        rag_context = self._format_rag_context(results)
        sources = [
            Source(
                document=r.chunk.source,
                snippet=r.chunk.text[:200] + ("..." if len(r.chunk.text) > 200 else ""),
                score=r.score,
            )
            for r in results
        ]

        # 2. Armar system prompt
        system = self._build_system_prompt(rag_context, page)

        # 3. Construir mensajes (historial + nuevo)
        messages = history + [{"role": "user", "content": user_message}]

        # 4. Llamar a Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=settings.claude_max_tokens,
                system=system,
                messages=messages,
            )
            reply_text = response.content[0].text if response.content else ""
            return reply_text, sources
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise


# Singleton
claude_service = ClaudeService()
