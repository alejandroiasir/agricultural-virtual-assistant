"""Routing de herramientas: parseo de la respuesta del LLM y rutas condicionales."""

import json
import logging
from typing import List

from haystack import component
from haystack.components.routers import ConditionalRouter

logger = logging.getLogger(__name__)


@component
class AnswerParser:
    """Convierte la respuesta JSON del LLM en el nombre de herramienta y la consulta."""

    @component.output_types(tool_name=str, query=str)
    def run(self, replies: List[str]):
        try:
            reply = json.loads(_strip_code_fence(replies[0]))
            return {"tool_name": reply["tool_name"], "query": reply["query"]}
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            # Sin herramienta válida ningún ConditionalRouter coincide y el chat responde con un aviso.
            logger.warning("No se pudo interpretar la respuesta del agente: %s", error)
            return {"tool_name": "", "query": ""}


def _strip_code_fence(text: str) -> str:
    """Quita los bloques ```json ... ``` que a veces devuelve el modelo."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return text


def _route(tool_name: str) -> dict:
    return {
        "condition": f"{{{{ tool_name == '{tool_name}' }}}}",
        "output": "{{query}}",
        "output_name": tool_name,
        "output_type": str,
    }


TOOL_ROUTES = [
    _route("weather_api"),
    _route("search_haystack"),
    _route("search_web"),
    _route("use_trained_knowledge"),
]


def build_tool_router() -> ConditionalRouter:
    return ConditionalRouter(TOOL_ROUTES)
