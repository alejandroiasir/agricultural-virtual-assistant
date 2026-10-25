"""Configuración del proyecto: variables de entorno y constantes."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Modelo usado por todos los componentes que generan texto.
LLM_MODEL = "gpt-4o-mini"

# Archivo TXT con la base de datos de empresas (una empresa por línea).
DATA_PATH = Path(os.getenv("AGROTECH_DATA_PATH", BASE_DIR / "data" / "empresas_agrotech.txt"))


def require_env(name: str) -> str:
    """Devuelve el valor de una variable de entorno o avisa de que falta."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. Añádela a tu archivo .env (ver .env.example)."
        )
    return value
