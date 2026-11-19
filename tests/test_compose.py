"""compose.yaml y la configuración de nginx, sin Docker: lo que se puede comprobar leyéndolos."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from litmar.api import app

yaml = pytest.importorskip("yaml")

RAIZ = Path(__file__).parent.parent
COMPOSE = yaml.safe_load((RAIZ / "compose.yaml").read_text(encoding="utf-8"))
NGINX = (RAIZ / "nginx" / "litmar.conf").read_text(encoding="utf-8")


def _rutas_reenviadas():
    """Rutas que nginx manda a la API: las de la expresión regular y las exactas (=)."""
    rutas = set()
    for grupo in re.findall(r"location ~ \^/\(([^)]*)\)\$", NGINX):
        rutas |= {"/" + ruta.replace("\\.", ".") for ruta in grupo.split("|")}
    rutas |= set(re.findall(r"location = (/\S+)", NGINX))
    return rutas


def test_nginx_reenvia_todas_las_rutas_de_la_api():
    contrato = set(TestClient(app).get("/openapi.json").json()["paths"])

    # /docs y /openapi.json no están en el contrato pero hacen falta para la documentación.
    assert _rutas_reenviadas() == contrato | {"/docs", "/openapi.json"}


def test_nginx_espera_varios_minutos_a_las_revisiones():
    bloque = re.search(r"location = /revisiones \{(.*?)\}", NGINX, re.S).group(1)

    assert "proxy_pass $api;" in bloque
    assert re.search(r"proxy_read_timeout\s+([5-9]|\d{2,})m;", bloque)


def test_nginx_usa_el_nombre_del_servicio():
    assert "set $api http://api:8000;" in NGINX
    assert "api" in COMPOSE["services"]


def test_la_api_escucha_en_todas_las_interfaces_del_contenedor():
    api = COMPOSE["services"]["api"]

    assert api["command"][:2] == ["litmar", "servir"]
    assert "0.0.0.0" in api["command"] and "8000" in api["command"]
    # Los puertos se publican solo para este ordenador: la API no tiene token (D-24).
    assert all(p.startswith("127.0.0.1:") for s in COMPOSE["services"].values() for p in s["ports"])


def test_el_env_llega_al_arrancar_y_solo_a_la_api():
    api, web = COMPOSE["services"]["api"], COMPOSE["services"]["web"]

    assert api["env_file"] == [{"path": ".env", "required": False}]
    assert "env_file" not in web and "environment" not in web


def test_web_monta_ficheros_que_existen():
    for volumen in COMPOSE["services"]["web"]["volumes"]:
        origen, _, resto = volumen.partition(":")
        assert (RAIZ / origen).exists(), origen
        assert resto.endswith(":ro")  # de solo lectura
    assert (RAIZ / "src" / "litmar" / "web" / "index.html").exists()
