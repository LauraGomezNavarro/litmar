"""Creación del modelo de lenguaje a partir de la configuración (ver .env.example).

El modelo se elige en la variable `LITMAR_MODELO` con el formato
`proveedor:modelo`. Cambiar de modelo es cambiar el `.env`: en el código no hay
ningún nombre de modelo ni ninguna clave.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

# Variables con la clave de cada proveedor, en orden de preferencia, y dónde se consigue.
CLAVES: dict[str, tuple[tuple[str, ...], str]] = {
    "google_genai": (("GOOGLE_API_KEY", "GEMINI_API_KEY"), "https://aistudio.google.com/apikey"),
    "anthropic": (("ANTHROPIC_API_KEY",), "https://console.anthropic.com/settings/keys"),
}

# El plan gratuito de Gemini admite pocas llamadas por minuto; por encima responde 429.
LLAMADAS_POR_MINUTO = 10

# Reintentos de la librería del proveedor ante errores como 503 o 429. Gemini hace 6
# por defecto: un fallo tarda minutos y cada reintento gasta cuota sin pasar por el
# limitador. Con 2, un fallo se ve en segundos.
MAX_REINTENTOS = 2


class ErrorConfiguracion(Exception):
    """Falta algo en el .env o tiene un valor no válido. El mensaje dice qué poner."""


def _valor(entorno: Mapping[str, str], clave: str) -> str | None:
    valor = entorno.get(clave, "").strip()
    return valor or None


def _llamadas_por_minuto(entorno: Mapping[str, str]) -> float:
    texto = _valor(entorno, "LITMAR_LLAMADAS_POR_MINUTO")
    if texto is None:
        return LLAMADAS_POR_MINUTO
    try:
        valor = float(texto)
    except ValueError:
        valor = 0
    if valor <= 0:
        raise ErrorConfiguracion(
            f"LITMAR_LLAMADAS_POR_MINUTO debe ser un número mayor que 0 (ahora: {texto!r})."
        )
    return valor


def crear_modelo(entorno: Mapping[str, str] | None = None) -> BaseChatModel:
    """Crea el modelo de chat configurado en `LITMAR_MODELO`.

    Sin `entorno`, lee el `.env` del directorio actual (las variables ya
    definidas tienen prioridad) y usa `os.environ`. Los tests pasan un
    diccionario para no leer el `.env` real.

    El modelo respeta un máximo de llamadas por minuto
    (`LITMAR_LLAMADAS_POR_MINUTO`, por defecto 10): si se piden más, espera en
    lugar de fallar.

    Lanza `ErrorConfiguracion` con un mensaje que dice qué añadir al `.env` si
    falta el modelo o la clave del proveedor.
    """
    if entorno is None:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True))
        entorno = os.environ

    modelo = _valor(entorno, "LITMAR_MODELO")
    if modelo is None:
        raise ErrorConfiguracion(
            "Falta LITMAR_MODELO en el .env. Añade una línea como "
            "LITMAR_MODELO=proveedor:modelo (hay ejemplos en .env.example)."
        )
    proveedor, separador, nombre = modelo.partition(":")
    proveedor, nombre = proveedor.strip(), nombre.strip()
    if not separador or not proveedor or not nombre:
        raise ErrorConfiguracion(
            f"LITMAR_MODELO debe tener el formato proveedor:modelo (ahora: {modelo!r}). "
            "Hay ejemplos en .env.example."
        )
    if proveedor not in CLAVES:
        raise ErrorConfiguracion(
            f"Proveedor {proveedor!r} no admitido en LITMAR_MODELO. "
            f"Usa uno de estos: {', '.join(CLAVES)}."
        )

    variables, donde = CLAVES[proveedor]
    clave = next(filter(None, (_valor(entorno, v) for v in variables)), None)
    if clave is None:
        raise ErrorConfiguracion(
            f"Falta la clave de {proveedor}. Añade al .env la línea "
            f"{variables[0]}=tu_clave (se consigue en {donde})."
        )

    from langchain.chat_models import init_chat_model
    from langchain_core.rate_limiters import InMemoryRateLimiter

    limitador = InMemoryRateLimiter(
        requests_per_second=_llamadas_por_minuto(entorno) / 60,
        max_bucket_size=1,  # sin ráfagas: las llamadas se reparten a lo largo del minuto
    )
    return init_chat_model(
        nombre,
        model_provider=proveedor,
        api_key=clave,
        rate_limiter=limitador,
        max_retries=MAX_REINTENTOS,
    )
