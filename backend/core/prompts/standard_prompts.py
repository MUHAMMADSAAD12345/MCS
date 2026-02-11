"""Prompt templates for Standard mode reasoning."""

STANDARD_PLAN_SYSTEM = """You are a reasoning planner. Given the user's query, output a JSON plan.
You must respond ONLY with valid JSON — no markdown, no explanation.

JSON schema:
{{
  "intent": "<question|task|analysis|creation>",
  "entities": ["<key terms extracted from query>"],
  "tools_needed": ["<rag|web_search|datetime|doc_create|none>"],
  "reasoning_notes": "<brief 1-2 sentence strategy for answering>"
}}

Tool descriptions:
- rag: Search user's uploaded documents for relevant context
- web_search: Search the web for current information
- datetime: Get current date and time
- doc_create: Generate a document (PDF/DOCX/XLSX)
- none: No tools needed, answer from knowledge

Only include tools that are truly necessary for the query."""


STANDARD_RESPOND_SYSTEM = """You are a helpful assistant. Answer the user's question using the provided context and tool results.
Think through your reasoning step-by-step internally, then give a clear, well-structured final answer.
Be thorough but not verbose. Use the provided information to ground your response."""


def build_plan_prompt(
    query: str,
    chat_history: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Build messages for the planning step."""
    messages = [{"role": "system", "content": STANDARD_PLAN_SYSTEM}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})
    return messages


def build_respond_prompt(
    query: str,
    plan_json: str,
    tool_results: str,
    rag_context: str | None = None,
    chat_history: list[dict] | None = None,
    datetime_info: str | None = None,
) -> list[dict[str, str]]:
    """Build messages for the synthesis / response step."""
    system_parts = [STANDARD_RESPOND_SYSTEM]
    if datetime_info:
        system_parts.append(f"\nCurrent date/time: {datetime_info}")

    messages = [{"role": "system", "content": "\n".join(system_parts)}]

    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Build rich user message
    parts = [f"My question: {query}"]
    if plan_json:
        parts.append(f"\nReasoning plan:\n{plan_json}")
    if rag_context:
        parts.append(f"\nDocument context:\n{rag_context}")
    if tool_results:
        parts.append(f"\nTool results:\n{tool_results}")

    messages.append({"role": "user", "content": "\n".join(parts)})
    return messages
