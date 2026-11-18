import pytest

from litmar.configuracion import FUENTES, crear_fuente, fuentes_disponibles
from litmar.fuentes import Arxiv, Crossref, EuropePMC, OpenAlex, Pangaea


def test_sin_configuracion_estan_todas_menos_zotero():
    assert fuentes_disponibles({}) == ["OpenAlex", "Crossref", "Europe PMC", "arXiv", "PANGAEA"]


@pytest.mark.parametrize("clave", ["ZOTERO_USER_ID", "ZOTERO_GROUP_ID"])
def test_zotero_disponible_con_usuario_o_grupo(clave):
    assert fuentes_disponibles({clave: "123"}) == list(FUENTES)


def test_variables_vacias_cuentan_como_ausentes():
    assert "Zotero" not in fuentes_disponibles({"ZOTERO_USER_ID": "  "})
    with crear_fuente("OpenAlex", {"OPENALEX_API_KEY": ""}) as fuente:
        assert fuente.api_key is None


@pytest.mark.parametrize(
    ("nombre", "clase"),
    [
        ("OpenAlex", OpenAlex),
        ("Crossref", Crossref),
        ("Europe PMC", EuropePMC),
        ("arXiv", Arxiv),
        ("PANGAEA", Pangaea),
    ],
)
def test_crea_cada_fuente(nombre, clase):
    with crear_fuente(nombre, {}) as fuente:
        assert type(fuente) is clase


def test_claves_del_entorno():
    entorno = {
        "OPENALEX_API_KEY": "clave-openalex",
        "CROSSREF_MAILTO": "alguien@example.org",
        "ZOTERO_GROUP_ID": "42",
        "ZOTERO_API_KEY": "clave-zotero",
    }
    with crear_fuente("OpenAlex", entorno) as openalex:
        assert openalex.api_key == "clave-openalex"
    with crear_fuente("Crossref", entorno) as crossref:
        assert crossref.mailto == "alguien@example.org"
    with crear_fuente("Zotero", entorno) as zotero:
        assert zotero.url.endswith("/groups/42/items")
        assert zotero.api_key == "clave-zotero"


def test_zotero_con_usuario_y_grupo_a_la_vez_es_un_error():
    with pytest.raises(ValueError):
        crear_fuente("Zotero", {"ZOTERO_USER_ID": "1", "ZOTERO_GROUP_ID": "2"})


def test_fuente_desconocida():
    with pytest.raises(ValueError, match="desconocida"):
        crear_fuente("Scopus", {})
