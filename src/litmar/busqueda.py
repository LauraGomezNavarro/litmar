"""Búsqueda en varias fuentes a la vez: la usan la CLI y la interfaz web."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import httpx

from litmar import configuracion
from litmar.biblioteca import Biblioteca
from litmar.fuentes import Fuente


@dataclass
class Resultado:
    """Artículos encontrados (sin duplicar DOI) y errores de las fuentes que fallaron."""

    library: Biblioteca = field(default_factory=Biblioteca)
    errors: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)  # nombres de las fuentes que fallaron


def buscar_en_fuentes(
    consulta: str,
    nombres: Iterable[str],
    n: int = 10,
    *,
    desde: int | None = None,
    crear: Callable[[str], Fuente] | None = None,
) -> Resultado:
    """Busca hasta `n` artículos en cada fuente y los junta sin duplicar DOI.

    Si una fuente falla se sigue con las demás. Los mensajes de error no incluyen
    la petición ni sus cabeceras, que podrían llevar claves. `crear` construye
    cada fuente a partir de su nombre (por defecto, `configuracion.crear_fuente`).
    """
    crear = crear or configuracion.crear_fuente
    resultado = Resultado()
    for nombre in nombres:
        try:
            with crear(nombre) as fuente:
                for articulo in fuente.buscar(consulta, n, desde=desde):
                    resultado.library.agregar(articulo)
            continue
        except httpx.HTTPStatusError as exc:
            error = f"{nombre} respondió con HTTP {exc.response.status_code}."
        except httpx.TransportError:
            error = f"{nombre}: no se pudo conectar tras los reintentos."
        except ValueError as exc:
            error = f"{nombre}: {exc}"
        resultado.errors.append(error)
        resultado.failed.append(nombre)
    return resultado
