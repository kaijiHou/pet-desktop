"""
AI Engine — OpenAI API integration for pet chat.
"""

from typing import Optional

from openai import OpenAI

from config import Config


class AIEngine:
    """Handles AI chat via OpenAI API."""

    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[OpenAI] = None
        self._conversation: list[dict] = []
        self._max_history = 20

    def _get_client(self) -> Optional[OpenAI]:
        if self._client is not None:
            return self._client
        key = self.config.api_key
        if not key:
            return None
        kwargs = {"api_key": key}
        base_url = self.config.get("openai_base_url", "")
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def reset_conversation(self):
        self._conversation = []

    def add_system_context(self, context: str):
        """Add extra system context (e.g., upcoming meetings)."""
        personality = self.config.get("ai_personality", "")
        name = self.config.get("ai_name", "Mochi")
        system_msg = {
            "role": "system",
            "content": (
                f"Kamu adalah {name}, seorang desktop pet kucing chibi.\n\n"
                f"{personality}\n\n"
                f"Context tambahan:\n{context}\n\n"
                "Gunakan bahasa Indonesia yang natural, kadang campur Inggris sedikit. "
                "Jawab dengan hangat dan personal. Maksimal 3-4 kalimat."
            ),
        }
        # Keep only the first system message, or update it
        if self._conversation and self._conversation[0]["role"] == "system":
            self._conversation[0] = system_msg
        else:
            self._conversation.insert(0, system_msg)

    def chat(self, message: str, context: str = "") -> str:
        """Send a message and get AI response (blocking)."""
        client = self._get_client()
        if not client:
            return (
                f"🔑 Aku belum punya API key nih!\n"
                "Buka settings dan masukin OpenAI API key dulu ya~"
            )

        # Update context
        self.add_system_context(context)

        # Add user message
        self._conversation.append({"role": "user", "content": message})

        try:
            response = client.chat.completions.create(
                model=self.config.api_model,
                messages=self._conversation,
                max_tokens=500,
                temperature=0.8,
            )
            reply = response.choices[0].message.content.strip()

            self._conversation.append({"role": "assistant", "content": reply})

            # Trim history if too long
            if len(self._conversation) > self._max_history:
                # Keep system + recent
                self._conversation = (
                    [self._conversation[0]] + self._conversation[-(self._max_history - 1):]
                )

            return reply

        except Exception as e:
            return f"😿 Hmm, aku error: {str(e)[:100]}"
