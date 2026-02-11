"""Prompt templates for Fast mode reasoning."""

FAST_SYSTEM = """You are a helpful assistant. Answer the user's question directly and concisely.
If context is provided, use it to inform your answer.
Do not explain your reasoning process — get straight to the answer.
Be accurate, clear, and brief."""


def build_fast_prompt(
    query: str,
    rag_context: str | None = None,
    chat_history: list[dict] | None = None,
    datetime_info: str | None = None,
) -> list[dict[str, str]]:
    """Build the message list for a single-pass fast response."""
    messages: list[dict[str, str]] = []

    # System prompt
    system_parts = [FAST_SYSTEM]
    if datetime_info:
        system_parts.append(f"\nCurrent date/time: {datetime_info}")
    messages.append({"role": "system", "content": "\n".join(system_parts)})

    # Chat history (last few messages for context)
    if chat_history:
        for msg in chat_history[-4:]:  # Keep it short for fast mode
            messages.append({"role": msg["role"], "content": msg["content"]})

    # User message with RAG context
    user_content = query
    if rag_context:
        user_content = f"Context from documents:\n{rag_context}\n\nQuestion: {query}"

    messages.append({"role": "user", "content": user_content})
    return messages
