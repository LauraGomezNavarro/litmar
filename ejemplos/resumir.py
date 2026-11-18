"""Práctica 1: busca 3 artículos sobre un tema y resume cada uno con resumir().

Ejecútalo desde la raíz del proyecto (necesita LITMAR_MODELO y la clave en el .env):

    uv run python ejemplos/resumir.py

Cambia TEMA y PREGUNTA por los de tu investigación. Después abre el DOI de uno de
los artículos y compara: ¿los hallazgos son fieles al original? ¿Ha inventado algo?
Prueba también con otro LITMAR_MODELO y compara los resultados.

Solo se envían al modelo datos públicos (título, autores y resumen del artículo).
"""

from litmar.busqueda import buscar_en_fuentes
from litmar.llm import ErrorConfiguracion, crear_modelo
from litmar.resumen import resumir

TEMA = "Posidonia oceanica carbon stock"  # la búsqueda, mejor en inglés
PREGUNTA = "¿Cuánto carbono almacenan las praderas de Posidonia oceanica?"
FUENTES = ["OpenAlex", "Europe PMC"]
N_ARTICULOS = 3


def main() -> None:
    try:
        modelo = crear_modelo()  # lee el .env
    except ErrorConfiguracion as exc:
        raise SystemExit(f"Error de configuración: {exc}") from None

    resultado = buscar_en_fuentes(TEMA, FUENTES, n=10)
    for error in resultado.errors:
        print(f"Aviso: {error}")

    # Solo los que tienen resumen: sin él, resumir() devuelve None y no llama al modelo.
    con_resumen = [a for a in resultado.library if a.abstract.strip()][:N_ARTICULOS]
    if not con_resumen:
        raise SystemExit(f"No se encontraron artículos con resumen sobre {TEMA!r}.")

    print(f"Pregunta: {PREGUNTA}")
    for i, articulo in enumerate(con_resumen, 1):
        print(f"\n[{i}/{len(con_resumen)}] {articulo.title}")
        print(f"    {articulo.short_citation} · https://doi.org/{articulo.doi}")
        try:
            resumen = resumir(articulo, PREGUNTA, modelo)
        except Exception as exc:  # p. ej. 503 si el modelo está saturado: se sigue con el resto
            motivo = str(exc).splitlines()[0][:200] if str(exc) else ""
            print(f"    No se pudo resumir ({type(exc).__name__}: {motivo})")
            continue
        print(f"    Relevancia: {resumen.relevancia}/5")
        print(f"    Objetivo: {resumen.objetivo}")
        print(f"    Método: {resumen.metodo}")
        print(f"    Hallazgos: {resumen.hallazgos}")
        print(f"    Limitaciones: {resumen.limitaciones}")


if __name__ == "__main__":
    main()
