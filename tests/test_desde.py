"""`buscar(..., desde=AÑO)` en todas las fuentes, con las respuestas guardadas."""

import json
from pathlib import Path

import httpx
import pytest

from litmar.fuentes import Arxiv, Crossref, EuropePMC, OpenAlex, Pangaea, Zotero

DATOS = Path(__file__).parent / "datos"


def filtro_openalex(p):
    assert p.url.params["filter"] == "publication_year:>2019"


def filtro_crossref(p):
    assert p.url.params["filter"] == "type:journal-article,from-pub-date:2020"


def filtro_europepmc(p):
    assert p.url.params["query"] == "(x) AND (PUB_YEAR:[2020 TO 9999])"


def filtro_arxiv(p):
    assert (
        p.url.params["search_query"] == "(all:x) AND submittedDate:[202001010000 TO 999912312359]"
    )


def filtro_pangaea(p):
    consulta = json.loads(p.url.params["source"])["query"]
    assert consulta["bool"]["filter"] == [{"range": {"agg-pubYear": {"gte": 2020}}}]
    assert consulta["bool"]["must"][0]["simple_query_string"]["query"] == "x"


def sin_filtro(p):
    """Zotero no tiene filtro de fecha: solo se aplica al convertir."""
    assert "2020" not in str(p.url)


FUENTES = [
    (OpenAlex, {}, "openalex_works.json", filtro_openalex),
    (Crossref, {}, "crossref_works.json", filtro_crossref),
    (EuropePMC, {}, "europepmc_search.json", filtro_europepmc),
    (Arxiv, {}, "arxiv_feed.xml", filtro_arxiv),
    (Pangaea, {}, "pangaea_search.json", filtro_pangaea),
    (Zotero, {"user_id": 1}, "zotero_items.json", sin_filtro),
]


def crear(clase, kwargs, fichero, peticiones):
    contenido = (DATOS / fichero).read_bytes()

    def manejar(peticion):
        peticiones.append(peticion)
        return httpx.Response(200, content=contenido)

    return clase(client=httpx.Client(transport=httpx.MockTransport(manejar)), **kwargs)


@pytest.mark.parametrize(
    ("clase", "kwargs", "fichero", "comprobar"), FUENTES, ids=lambda x: getattr(x, "__name__", "")
)
def test_desde_se_envia_a_la_api_y_se_comprueba(clase, kwargs, fichero, comprobar):
    # n grande: la respuesta guardada cabe en una sola página.
    todos = crear(clase, kwargs, fichero, []).buscar("x", n=1000)
    peticiones = []
    filtrados = crear(clase, kwargs, fichero, peticiones).buscar("x", n=1000, desde=2020)
    comprobar(peticiones[0])
    # La comprobación local descarta lo anterior a 2020 aunque la API lo devuelva.
    assert filtrados == [a for a in todos if a.year >= 2020]


@pytest.mark.parametrize(
    ("clase", "kwargs", "fichero", "comprobar"), FUENTES, ids=lambda x: getattr(x, "__name__", "")
)
def test_sin_desde_no_hay_filtro(clase, kwargs, fichero, comprobar):
    peticiones = []
    crear(clase, kwargs, fichero, peticiones).buscar("x", n=1000)
    assert "2020" not in str(peticiones[0].url)
    assert "PUB_YEAR" not in str(peticiones[0].url)
