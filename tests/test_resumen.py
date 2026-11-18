"""Tests de resumir() con un modelo falso: sin clave, sin red y sin gastar tokens."""

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from litmar.resumen import ResumenArticulo, resumir

RESUMEN_FIJO = ResumenArticulo(
    objetivo="Medir el carbono almacenado en praderas de posidonia.",
    metodo="Testigos de sedimento en 10 praderas del Mediterráneo.",
    hallazgos="Almacenan de media 300 t C/ha.",
    relevancia=5,
    limitaciones="Solo praderas someras.",
)


class ModeloFalso:
    """Imita la parte de un modelo de chat de LangChain que usa resumir().

    Guarda el esquema pedido y los mensajes recibidos, y siempre devuelve
    RESUMEN_FIJO.
    """

    def __init__(self):
        self.esquema = None
        self.mensajes = None
        self.llamadas = 0

    def with_structured_output(self, esquema):
        self.esquema = esquema
        return RunnableLambda(self._responder)

    def _responder(self, mensajes):
        self.llamadas += 1
        self.mensajes = mensajes
        return RESUMEN_FIJO


def texto_enviado(modelo: ModeloFalso) -> str:
    return "\n".join(contenido for _, contenido in modelo.mensajes)


def test_resumir_devuelve_el_objeto_estructurado(hacer_articulo):
    modelo = ModeloFalso()
    resumen = resumir(hacer_articulo(), "¿Cuánto carbono guarda la posidonia?", modelo)

    assert resumen == RESUMEN_FIJO
    assert modelo.esquema is ResumenArticulo
    assert modelo.llamadas == 1


def test_resumir_envia_pregunta_titulo_autores_ano_y_resumen(hacer_articulo):
    articulo = hacer_articulo(
        title="Carbono azul",
        authors=["García, Ana", "López, Juan"],
        year=2021,
        abstract="Medimos el carbono.",
    )
    modelo = ModeloFalso()
    resumir(articulo, "¿Cuánto carbono guarda la posidonia?", modelo)

    texto = texto_enviado(modelo)
    assert "¿Cuánto carbono guarda la posidonia?" in texto
    assert "Título: Carbono azul" in texto
    assert "Autores: García, Ana; López, Juan" in texto
    assert "Año: 2021" in texto
    assert "Medimos el carbono." in texto


@pytest.mark.parametrize("abstract", ["", "   \n"])
def test_sin_resumen_no_llama_al_modelo(hacer_articulo, abstract):
    modelo = ModeloFalso()
    assert resumir(hacer_articulo(abstract=abstract), "pregunta", modelo) is None
    assert modelo.llamadas == 0
    assert modelo.esquema is None


def test_cada_campo_tiene_descripcion():
    # El modelo lee estas descripciones: son parte del prompt.
    for nombre, campo in ResumenArticulo.model_fields.items():
        assert campo.description, f"el campo {nombre} no tiene descripción"


@pytest.mark.parametrize("relevancia", [0, 6])
def test_relevancia_fuera_de_rango_no_valida(relevancia):
    datos = RESUMEN_FIJO.model_dump() | {"relevancia": relevancia}
    with pytest.raises(ValidationError):
        ResumenArticulo(**datos)
