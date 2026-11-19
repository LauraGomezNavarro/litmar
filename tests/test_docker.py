"""Dockerfile y .dockerignore, sin Docker: orden de las capas, usuario y qué entra en la imagen."""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
DOCKERFILE = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
INSTRUCCIONES = [
    linea.strip() for linea in DOCKERFILE.splitlines() if re.match(r"[A-Z]+\s", linea.strip())
]


def _indice(prefijo):
    return next(i for i, linea in enumerate(INSTRUCCIONES) if linea.startswith(prefijo))


def _patron(regla):
    """Una regla de .dockerignore como la entiende Docker: rutas desde la raíz del
    contexto, `*` no cruza `/`, `**/` vale en cualquier carpeta y una carpeta
    excluida excluye todo su contenido. (No es como .gitignore.)"""
    regex = ""
    for parte in re.split(r"(\*\*/|\*\*|\*|\?|\[[^\]]*\])", regla.strip("/")):
        regex += {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}.get(
            parte, parte if parte.startswith("[") else re.escape(parte)
        )
    return re.compile(regex + "(?:/.*)?$")


REGLAS = [
    (linea.startswith("!"), _patron(linea.lstrip("!")))
    for linea in map(str.strip, (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines())
    if linea and not linea.startswith("#")
]


def entra_en_la_imagen(ruta):
    excluida = False
    for excepcion, patron in REGLAS:  # gana la última regla que coincide
        if patron.match(ruta):
            excluida = not excepcion
    return not excluida


@pytest.mark.parametrize(
    "ruta",
    [
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "README.md",  # pyproject.toml lo declara: sin él, uv sync falla
        "src/litmar/api.py",
        "src/litmar/web/index.html",
    ],
)
def test_entra_lo_necesario(ruta):
    assert entra_en_la_imagen(ruta)


@pytest.mark.parametrize(
    "ruta",
    [
        ".env",
        ".env.produccion",
        ".venv/bin/python",
        ".git/HEAD",
        ".claude/settings.local.json",
        "tests/test_api.py",
        "docs/Clase3.pdf",
        "ejemplos/revisiones/2026-11-19_pregunta/revision.md",
        "src/litmar/__pycache__/api.cpython-312.pyc",
        "src/litmar/.DS_Store",
        "AGENTS.md",
        "PROGRESS.md",
        "compose.yaml",
        "nginx/litmar.conf",
    ],
)
def test_no_entran_secretos_ni_lo_que_sobra(ruta):
    assert not entra_en_la_imagen(ruta)


def test_dependencias_antes_que_el_codigo():
    # La capa de dependencias solo depende de estos ficheros: se reutiliza al cambiar el código.
    orden = [
        "COPY pyproject.toml uv.lock",
        "uv sync --locked --no-install-project",
        "COPY . .",
        "uv sync --locked\n",  # y después, el proyecto
    ]
    posiciones = [DOCKERFILE.index(paso) for paso in orden]
    assert posiciones == sorted(posiciones)


def test_sin_dependencias_de_desarrollo_y_versiones_fijas():
    assert "UV_NO_DEV=1" in DOCKERFILE
    assert INSTRUCCIONES[0] == "FROM python:3.12-slim"
    assert re.search(r"COPY --from=ghcr\.io/astral-sh/uv:\d+\.\d+\.\d+ /uv /bin/uv", DOCKERFILE)


def test_usuario_sin_privilegios_y_sin_secretos():
    assert _indice("USER app") < _indice("CMD")
    # Ninguna clave en ENV o ARG: se pasan al arrancar el contenedor.
    variables = " ".join(linea for linea in INSTRUCCIONES if linea.startswith(("ENV", "ARG")))
    assert not re.search(r"KEY|TOKEN|SECRET|PASSWORD|MAILTO|LITMAR_MODELO", variables)


def test_arranca_la_api_en_todas_las_interfaces():
    cmd = INSTRUCCIONES[_indice("CMD")]

    assert cmd == 'CMD ["litmar", "servir", "--host", "0.0.0.0", "--puerto", "8000"]'
    assert "EXPOSE 8000" in INSTRUCCIONES
