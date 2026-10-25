"""Memoria de conversación: historial en RAM y persistencia en Supabase."""

import uuid

from haystack import component
from supabase import Client, create_client

from config import require_env


@component
class ConversationMemory:
    def __init__(self, session_id: str | None = None):
        self.chat_history: list[dict] = []
        self.session_id = session_id or str(uuid.uuid4())
        self.supabase: Client = create_client(require_env("SUPABASE_URL"), require_env("SUPABASE_KEY"))

    @component.output_types(memory=str)
    def run(self, query: str):
        self._add_message("user", query)
        return {"memory": self.get_formatted_history()}

    def update_with_response(self, response: str):
        self._add_message("assistant", response)

    def load_from_db(self):
        """Recupera el historial de esta sesión desde Supabase."""
        response = (
            self.supabase.table("conversaciones")
            .select("*")
            .eq("session_id", self.session_id)
            .order("timestamp", desc=False)
            .execute()
        )
        self.chat_history = [{"role": msg["role"], "content": msg["content"]} for msg in response.data]

    def get_formatted_history(self) -> str:
        """Devuelve todo el historial formateado."""
        return "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.chat_history)

    def _add_message(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
        self.supabase.table("conversaciones").insert({
            "session_id": self.session_id,
            "role": role,
            "content": content,
        }).execute()
