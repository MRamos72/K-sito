"""
Configuración por ruta para experience.viveenlabaja.mx
Define saludos contextuales, sugerencias rápidas y guías de formularios.
"""
from __future__ import annotations

from fnmatch import fnmatch

from app.models.schemas import FormStep, Suggestion


SITE_CONFIG = {
    # Páginas registradas del sitio
    "pages": [
        {
            "url": "https://experience.viveenlabaja.mx/",
            "path": "https://experience.viveenlabaja.mx/",
            "title": "vive la baja",
        },
    ],

    # Saludos por patrón de URL
    "greetings": {
        "/pago*": "¡Órale! Estoy aquí para guiarte con tu pago 🌱 ¿Tienes ya tu número de referencia?",
        "/pagar*": "¡Órale! Estoy aquí para guiarte con tu pago 🌱 ¿Tienes ya tu número de referencia?",
        "/desarrollo*": "¡Qué padre! Explora nuestros desarrollos 🏡 ¿Prefieres playa, campo o cerca de la Ruta del Vino?",
        "/contacto*": "¡Hola! ¿Te paso al WhatsApp de cobranza o te ayudo yo con tu duda? 🌱",
        "/comprobante*": "¡Va! Te ayudo a enviar tu comprobante 📄 ¿Ya hiciste el pago?",
        "/": "¡Hola! Soy T-rrenito 🌱 tu guía en Vive en la Baja. ¿Buscas un terreno o necesitas ayuda con un pago?",
    },
    "default_greeting": "¡Hola! Soy T-rrenito 🌱 tu asistente de Vive en la Baja. ¿Te ayudo con un pago o info de los desarrollos?",

    # Sugerencias rápidas por patrón de URL
    "suggestions": {
        "/pago*": [
            ("¿Cómo pago por SPEI?", "¿Cómo hago un pago por SPEI en pesos?"),
            ("Pago en efectivo", "¿Cómo pago en efectivo en Santander?"),
            ("Pago con cheque", "¿Cómo pago con cheque?"),
            ("⚠️ Mi referencia", "¿Cómo obtengo mi número de referencia?"),
        ],
        "/desarrollo*": [
            ("Desarrollos en Rosarito", "¿Qué desarrollos tienen en Rosarito?"),
            ("Desarrollos en Tijuana", "¿Qué desarrollos tienen en Tijuana?"),
            ("Cerca de la Ruta del Vino", "¿Qué desarrollos hay cerca del Valle de Guadalupe?"),
        ],
        "/comprobante*": [
            ("¿Cómo envío el comprobante?", "¿Cómo envío mi comprobante de pago?"),
            ("¿A qué correo?", "¿A qué correo mando mi comprobante?"),
            ("¿Qué pongo en el asunto?", "¿Qué asunto debe llevar el correo del comprobante?"),
        ],
    },
    "default_suggestions": [
        ("¿Cómo hago un pago?", "¿Cómo hago un pago?"),
        ("Ver desarrollos", "¿Qué desarrollos tienen disponibles?"),
        ("¿Qué es la referencia?", "¿Qué es el número de referencia?"),
    ],

    # Guías de formularios — Modo Clippy
    "form_guides": {
        "*pago*": [
            {"selector": "input[name='nombre'], #nombre", "message": "📝 Tu <b>nombre completo</b> exactamente como aparece en tu contrato"},
            {"selector": "select[name='desarrollo'], #desarrollo", "message": "🏖️ Selecciona tu <b>desarrollo</b> (Sahara, Toscana, Las Puertas...)"},
            {"selector": "input[name='referencia'], #referencia", "message": "⚠️ Tu <b>número de referencia</b> es obligatorio. Pídelo al WhatsApp <b>664 912 0331</b>"},
            {"selector": "select[name='metodo'], #metodo", "message": "💳 Elige método: <b>SPEI</b> (más rápido), <b>efectivo</b> o <b>cheque</b> en Santander"},
            {"selector": "input[name='monto'], #monto", "message": "💰 El <b>monto a pagar</b>. Confírmalo al WhatsApp si no lo tienes"},
        ],
    },
}


def get_greeting(path: str) -> str:
    for pattern, msg in SITE_CONFIG["greetings"].items():
        if fnmatch(path, pattern):
            return msg
    return SITE_CONFIG["default_greeting"]


def get_suggestions(path: str) -> list[Suggestion]:
    items: list[tuple[str, str]] = SITE_CONFIG["default_suggestions"]
    for pattern, sugg_list in SITE_CONFIG["suggestions"].items():
        if fnmatch(path, pattern):
            items = sugg_list
            break
    return [Suggestion(text=t, action=a) for t, a in items]


def get_form_steps(path: str) -> list[FormStep]:
    for pattern, steps in SITE_CONFIG["form_guides"].items():
        if fnmatch(path, pattern):
            return [FormStep(**s) for s in steps]
    return []
