"""Resumen estructurado de un artículo con un LLM.

El modelo no devuelve texto libre, sino un objeto `ResumenArticulo` validado por
Pydantic. Las descripciones de cada campo forman parte del prompt: el modelo las
lee para saber qué poner en cada uno.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from litmar.articulo import Articulo


class ResumenArticulo(BaseModel):
    """Resumen estructurado de un artículo científico, hecho a partir de su resumen."""

    objetivo: str = Field(
        description="Qué pregunta o problema aborda el artículo, en una o dos frases."
    )
    metodo: str = Field(
        description="Cómo lo estudia: tipo de estudio, datos, zona, técnicas o modelos usados."
    )
    hallazgos: str = Field(
        description="Resultados y conclusiones principales, con las cifras que dé el resumen."
    )
    relevancia: int = Field(
        ge=1,
        le=5,
        description=(
            "Relevancia del artículo para la pregunta de investigación: 1 = nada "
            "relevante, 3 = relacionado de forma indirecta, 5 = responde directamente."
        ),
    )
    limitaciones: str = Field(
        description=(
            "Limitaciones del estudio que se deducen del resumen. Si el resumen no "
            "permite saberlo, escribe «No se indican en el resumen»."
        )
    )


INSTRUCCIONES = (
    "Eres un asistente de revisión bibliográfica. Resume el artículo usando solo "
    "la información de su título y su resumen: no añadas datos que no aparezcan "
    "ahí. Si un campo no se puede deducir del texto, dilo en lugar de inventarlo. "
    "Responde en español."
)


def resumir(articulo: Articulo, pregunta: str, modelo: BaseChatModel) -> ResumenArticulo | None:
    """Resume `articulo` y puntúa su relevancia para `pregunta`.

    `modelo` es cualquier modelo de chat de LangChain. Si el artículo no tiene
    resumen, devuelve `None` sin llamar al modelo: con solo el título, el modelo
    tendría que inventarse el método y los hallazgos.
    """
    if not articulo.abstract.strip():
        return None

    estructurado = modelo.with_structured_output(ResumenArticulo)
    mensajes = [
        ("system", INSTRUCCIONES),
        (
            "human",
            f"Pregunta de investigación: {pregunta}\n\n"
            f"Título: {articulo.title}\n"
            f"Autores: {'; '.join(articulo.authors)}\n"
            f"Año: {articulo.year}\n"
            f"Revista: {articulo.journal}\n"
            f"Resumen:\n{articulo.abstract.strip()}",
        ),
    ]
    return estructurado.invoke(mensajes)
