"""Tests de crear_modelo(): crean el objeto del modelo, pero no lo llaman (sin red ni tokens)."""

import pytest

from litmar import llm
from litmar.llm import ErrorConfiguracion, crear_modelo

GEMINI = {"LITMAR_MODELO": "google_genai:gemini-prueba", "GOOGLE_API_KEY": "clave-falsa"}


def test_crea_el_modelo_de_gemini():
    modelo = crear_modelo(GEMINI)
    assert type(modelo).__name__ == "ChatGoogleGenerativeAI"
    assert modelo.model.endswith("gemini-prueba")
    assert modelo.google_api_key.get_secret_value() == "clave-falsa"


def test_crea_el_modelo_de_anthropic():
    modelo = crear_modelo(
        {"LITMAR_MODELO": "anthropic:claude-prueba", "ANTHROPIC_API_KEY": "clave-falsa"}
    )
    assert type(modelo).__name__ == "ChatAnthropic"
    assert modelo.model == "claude-prueba"


@pytest.mark.parametrize(
    "entorno",
    [GEMINI, {"LITMAR_MODELO": "anthropic:claude-prueba", "ANTHROPIC_API_KEY": "x"}],
)
def test_limita_los_reintentos(entorno):
    assert crear_modelo(entorno).max_retries == llm.MAX_REINTENTOS == 2


def test_acepta_gemini_api_key():
    modelo = crear_modelo({"LITMAR_MODELO": "google_genai:gemini-prueba", "GEMINI_API_KEY": "x"})
    assert modelo.google_api_key.get_secret_value() == "x"


def test_limite_de_llamadas_por_defecto():
    limitador = crear_modelo(GEMINI).rate_limiter
    assert limitador.requests_per_second == pytest.approx(llm.LLAMADAS_POR_MINUTO / 60)
    assert limitador.max_bucket_size == 1


def test_limite_de_llamadas_configurable():
    limitador = crear_modelo(GEMINI | {"LITMAR_LLAMADAS_POR_MINUTO": "30"}).rate_limiter
    assert limitador.requests_per_second == pytest.approx(0.5)


@pytest.mark.parametrize("valor", ["0", "-5", "muchas"])
def test_limite_de_llamadas_no_valido(valor):
    with pytest.raises(ErrorConfiguracion, match="LITMAR_LLAMADAS_POR_MINUTO"):
        crear_modelo(GEMINI | {"LITMAR_LLAMADAS_POR_MINUTO": valor})


@pytest.mark.parametrize("entorno", [{}, {"LITMAR_MODELO": "  "}])
def test_sin_modelo_dice_que_poner(entorno):
    with pytest.raises(ErrorConfiguracion, match=r"Falta LITMAR_MODELO en el \.env"):
        crear_modelo(entorno)


@pytest.mark.parametrize("modelo", ["gemini-prueba", "google_genai:", ":gemini-prueba"])
def test_formato_no_valido(modelo):
    with pytest.raises(ErrorConfiguracion, match="proveedor:modelo"):
        crear_modelo({"LITMAR_MODELO": modelo, "GOOGLE_API_KEY": "x"})


def test_proveedor_no_admitido():
    with pytest.raises(ErrorConfiguracion, match="google_genai, anthropic"):
        crear_modelo({"LITMAR_MODELO": "inventado:modelo"})


@pytest.mark.parametrize(
    ("modelo", "variable"),
    [("google_genai:gemini-prueba", "GOOGLE_API_KEY"), ("anthropic:claude", "ANTHROPIC_API_KEY")],
)
def test_sin_clave_dice_que_poner_en_el_env(modelo, variable):
    with pytest.raises(ErrorConfiguracion, match=rf"Añade al \.env la línea {variable}=tu_clave"):
        crear_modelo({"LITMAR_MODELO": modelo, variable: "  "})


def test_con_entorno_no_lee_el_env(monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("no debe leer el .env real")

    monkeypatch.setattr("dotenv.load_dotenv", prohibido)
    crear_modelo(GEMINI)


def test_sin_entorno_lee_el_env_y_las_variables_del_sistema(monkeypatch):
    leidos = []
    # Se sustituye la lectura del .env para no cargar el .env real del proyecto.
    monkeypatch.setattr("dotenv.find_dotenv", lambda **kwargs: "/ruta/.env")
    monkeypatch.setattr("dotenv.load_dotenv", leidos.append)
    monkeypatch.setenv("LITMAR_MODELO", "anthropic:claude-prueba")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa")

    assert crear_modelo().model == "claude-prueba"
    assert leidos == ["/ruta/.env"]
