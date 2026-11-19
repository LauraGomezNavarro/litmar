# Imagen de litmar para servir la API (litmar servir). Se construye con:
#   docker build -t litmar .        o, con la web delante,  docker compose up --build
# Las claves NO van en la imagen: se pasan al arrancar (--env-file .env, o env_file en compose).

# Base: Python 3.12 oficial en su variante «slim» (Debian sin extras: imagen pequeña).
FROM python:3.12-slim

# uv desde la imagen oficial de Astral. La versión es fija y la misma que generó
# uv.lock: así la imagen se construye igual hoy que dentro de seis meses.
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv

# Configuración de uv para la imagen:
# - UV_NO_DEV=1: sin el grupo dev (pytest, ruff, Streamlit); el extra «ui» tampoco entra.
# - UV_PYTHON_DOWNLOADS=0: usar el Python de la imagen, no descargar otro.
# - UV_COMPILE_BYTECODE=1: compilar a .pyc al instalar; arranca antes y el usuario
#   sin permisos de escritura no tiene que hacerlo.
# - UV_LINK_MODE=copy: copiar desde la caché (la caché está en otro disco; enlazar no se puede).
ENV UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Carpeta de trabajo dentro de la imagen: aquí van el código y el entorno (.venv).
WORKDIR /app

# Primero, SOLO lo que define las dependencias. Cambia poco, así que la capa
# siguiente (la lenta) se reutiliza mientras no cambien estos tres ficheros.
COPY pyproject.toml uv.lock .python-version ./

# Instala las dependencias exactas de uv.lock (--locked: falla si el lock no
# coincide con pyproject.toml), todavía sin litmar (--no-install-project). La
# caché de uv se monta solo durante este paso: acelera y no engorda la imagen.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Después, el código, que cambia siempre. Lo que no debe entrar (.env, .venv,
# .git, tests…) lo excluye .dockerignore.
COPY . .

# Ahora sí instala litmar. Las dependencias ya están: este paso tarda segundos.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Los programas del entorno (litmar, uvicorn) delante en el PATH: se ejecutan
# directamente, sin `uv run` (que intentaría sincronizar .venv y no tiene permiso).
ENV PATH="/app/.venv/bin:$PATH"

# Un usuario sin privilegios: si alguien aprovechara un fallo de la API, no
# sería administrador del contenedor. El código y .venv siguen siendo de root:
# el usuario puede leerlos y ejecutarlos, pero no modificarlos.
RUN useradd --create-home app

# A partir de aquí, todo se ejecuta como «app».
USER app

# Documenta el puerto en el que escucha la API (publicarlo es cosa de -p o de compose).
EXPOSE 8000

# Al arrancar: la API en todas las interfaces del contenedor (0.0.0.0); con
# 127.0.0.1 solo se la podría llamar desde dentro del propio contenedor.
CMD ["litmar", "servir", "--host", "0.0.0.0", "--puerto", "8000"]
