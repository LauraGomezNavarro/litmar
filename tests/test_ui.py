from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from litmar.fuentes import Fuente

UI = str(Path(__file__).parent.parent / "src" / "litmar" / "ui.py")


class FuenteFalsa(Fuente):
    def __init__(self, articulos=(), error=None):
        super().__init__()
        self.articulos = list(articulos)
        self.error = error

    def buscar(self, consulta, n=10, *, desde=None):
        if self.error:
            raise self.error
        return self.articulos[:n]


@pytest.fixture
def fuentes(monkeypatch, hacer_articulo):
    """Sustituye las fuentes reales: OpenAlex y Crossref comparten un DOI."""
    comun = hacer_articulo()
    fuentes = {
        "OpenAlex": FuenteFalsa([comun, hacer_articulo(doi="10.1/a", year=2019)]),
        "Crossref": FuenteFalsa([comun, hacer_articulo(doi="10.1/b", citations=7)]),
        "arXiv": FuenteFalsa(
            error=httpx.HTTPStatusError(
                "fallo", request=httpx.Request("GET", "https://x"), response=httpx.Response(503)
            )
        ),
    }
    monkeypatch.setattr("litmar.configuracion.crear_fuente", lambda nombre: fuentes[nombre])
    monkeypatch.delenv("ZOTERO_USER_ID", raising=False)
    monkeypatch.delenv("ZOTERO_GROUP_ID", raising=False)
    return fuentes


def buscar(consulta, nombres, n=10):
    app = AppTest.from_file(UI, default_timeout=30).run()
    app.text_input[0].input(consulta)
    app.multiselect[0].set_value(nombres)
    app.number_input[0].set_value(n)
    return app.button[0].click().run()


def test_busca_en_varias_fuentes_sin_duplicar(fuentes):
    app = buscar("redes", ["OpenAlex", "Crossref"])
    assert not app.exception
    tabla = app.dataframe[0].value
    assert list(tabla.columns) == ["Año", "Citas", "Autores", "Título", "DOI"]
    assert len(tabla) == 3
    assert tabla["DOI"].tolist() == [
        "https://doi.org/10.1000/xyz123",
        "https://doi.org/10.1/a",
        "https://doi.org/10.1/b",
    ]
    assert app.subheader[0].value == "3 artículos"


def test_numero_de_resultados_por_fuente(fuentes):
    app = buscar("redes", ["OpenAlex"], n=1)
    assert len(app.dataframe[0].value) == 1


def test_una_fuente_que_falla_no_impide_ver_las_demas(fuentes):
    app = buscar("redes", ["OpenAlex", "arXiv"])
    assert [e.value for e in app.error] == ["arXiv respondió con HTTP 503."]
    assert len(app.dataframe[0].value) == 2


def test_consulta_vacia_no_busca(fuentes):
    app = buscar("   ", ["OpenAlex"])
    assert app.warning[0].value == "Escribe algo que buscar."
    assert not app.dataframe


def test_zotero_solo_aparece_si_esta_configurado(fuentes, monkeypatch):
    assert "Zotero" not in AppTest.from_file(UI, default_timeout=30).run().multiselect[0].options
    monkeypatch.setenv("ZOTERO_USER_ID", "123")
    assert "Zotero" in AppTest.from_file(UI, default_timeout=30).run().multiselect[0].options
