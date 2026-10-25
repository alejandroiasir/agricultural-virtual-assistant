"""Construye el agente: router de herramientas + RAG + búsqueda web + clima + conocimiento del modelo."""

import logging

from haystack import Document, Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.websearch.serper_dev import SerperDevWebSearch
from haystack.document_stores.in_memory import InMemoryDocumentStore

from config import DATA_PATH, LLM_MODEL, require_env
from memory import ConversationMemory
from prompts import (
    AGENT_PROMPT_TEMPLATE,
    RAG_PROMPT_TEMPLATE,
    TRAINED_KNOWLEDGE_PROMPT_TEMPLATE,
    WEBSEARCH_PROMPT_TEMPLATE,
)
from router import AnswerParser, build_tool_router
from weather import GetCurrentWeather

logger = logging.getLogger(__name__)

NO_ANSWER_MESSAGE = "No se encontró una respuesta válida."


def load_documents(path=DATA_PATH) -> list[Document]:
    """Lee el TXT de empresas y crea un Document por línea no vacía."""
    if not path.exists():
        raise FileNotFoundError(
            f"No encuentro la base de datos en {path}. Define AGROTECH_DATA_PATH en tu .env."
        )
    with open(path, "r", encoding="utf-8") as file:
        return [Document(content=line.strip()) for line in file if line.strip()]


def _llm() -> OpenAIGenerator:
    return OpenAIGenerator(model=LLM_MODEL)


def build_agent() -> tuple[Pipeline, ConversationMemory]:
    """Devuelve el pipeline del agente y la memoria de conversación que usa."""
    document_store = InMemoryDocumentStore()
    document_store.write_documents(load_documents())

    memory = ConversationMemory()

    agent = Pipeline()

    # Agente: decide qué herramienta usar
    agent.add_component("memory", memory)
    agent.add_component(
        "prompt_builder_for_agent",
        PromptBuilder(template=AGENT_PROMPT_TEMPLATE, required_variables=["memory", "query"]),
    )
    agent.add_component("llm_for_agent", _llm())
    agent.add_component("answer_parser", AnswerParser())
    agent.add_component("tool_router", build_tool_router())

    # Búsqueda web
    agent.add_component("websearch", SerperDevWebSearch())
    agent.add_component(
        "prompt_builder_for_websearch",
        PromptBuilder(template=WEBSEARCH_PROMPT_TEMPLATE, required_variables=["documents", "query"]),
    )
    agent.add_component("llm_for_web", _llm())

    # RAG sobre la base de datos de empresas
    agent.add_component("retriever", InMemoryBM25Retriever(document_store=document_store))
    agent.add_component(
        "prompt_builder_for_rag",
        PromptBuilder(template=RAG_PROMPT_TEMPLATE, required_variables=["documents", "query"]),
    )
    agent.add_component("llm_for_rag", _llm())

    # Clima
    agent.add_component("get_weather", GetCurrentWeather(require_env("WEATHER_API")))

    # Conocimiento entrenado del modelo
    agent.add_component(
        "prompt_builder_for_trained_knowledge",
        PromptBuilder(template=TRAINED_KNOWLEDGE_PROMPT_TEMPLATE, required_variables=["query"]),
    )
    agent.add_component("llm_for_trained_knowledge", _llm())

    # Conexiones: memoria -> prompt del agente -> LLM -> parser -> router
    agent.connect("memory.memory", "prompt_builder_for_agent.memory")
    agent.connect("prompt_builder_for_agent", "llm_for_agent")
    agent.connect("llm_for_agent", "answer_parser")
    agent.connect("answer_parser.query", "tool_router.query")
    agent.connect("answer_parser.tool_name", "tool_router.tool_name")

    # Web search
    agent.connect("tool_router.search_web", "websearch.query")
    agent.connect("tool_router.search_web", "prompt_builder_for_websearch.query")
    agent.connect("websearch.documents", "prompt_builder_for_websearch.documents")
    agent.connect("prompt_builder_for_websearch", "llm_for_web")

    # RAG
    agent.connect("tool_router.search_haystack", "retriever.query")
    agent.connect("tool_router.search_haystack", "prompt_builder_for_rag.query")
    agent.connect("retriever.documents", "prompt_builder_for_rag.documents")
    agent.connect("prompt_builder_for_rag", "llm_for_rag")

    # Clima
    agent.connect("tool_router.weather_api", "get_weather.city")

    # Conocimiento entrenado
    agent.connect("tool_router.use_trained_knowledge", "prompt_builder_for_trained_knowledge.query")
    agent.connect("prompt_builder_for_trained_knowledge", "llm_for_trained_knowledge")

    return agent, memory


def answer_question(agent: Pipeline, memory: ConversationMemory, message: str) -> str:
    """Ejecuta el agente con una pregunta y devuelve la respuesta en texto."""
    response = agent.run({
        "prompt_builder_for_agent": {"query": message},
        "memory": {"query": message},
    })
    answer = _extract_answer(response)
    memory.update_with_response(answer)
    return answer


def _extract_answer(response: dict) -> str:
    # Solo la rama tomada por el router produce salida, así que basta con buscar la primera que exista.
    if "llm_for_web" in response:
        return response["llm_for_web"]["replies"][0]
    if "llm_for_rag" in response:
        return response["llm_for_rag"]["replies"][0]
    if "llm_for_trained_knowledge" in response:
        return response["llm_for_trained_knowledge"]["replies"][0]
    if "get_weather" in response:
        return response["get_weather"]["text"]
    logger.warning("El agente no produjo respuesta: %s", response)
    return NO_ANSWER_MESSAGE
