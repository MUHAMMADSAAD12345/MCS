"""Prompt templates for Deep mode reasoning."""

DEEP_DECOMPOSE_SYSTEM = """You are a research planner. Break the user's complex question into 2-4 independent sub-questions that, when answered together, will fully address the original query.

You must respond ONLY with valid JSON — no markdown, no explanation.

JSON schema:
{{
  "sub_questions": [
    {{
      "id": 1,
      "question": "<specific sub-question>",
      "tools": ["<rag|web_search|web_deep|datetime>"],
      "search_queries": ["<specific search terms for web/rag>"]
    }}
  ],
  "synthesis_strategy": "<1-2 sentence description of how to combine sub-answers into a final answer>"
}}

Tool descriptions:
- rag: Search user's uploaded documents
- web_search: Quick web search (DuckDuckGo)
- web_deep: Deep web search with detailed results (Tavily)
- datetime: Get current date and time

Guidelines:
- Each sub-question should be answerable independently
- Include specific search queries for tools to use
- Keep sub-questions focused and non-overlapping"""


DEEP_SUB_ANSWER_SYSTEM = """You are a thorough researcher. Answer the given sub-question using the provided context.
Be factual and detailed. Cite sources when available. Focus only on the specific sub-question asked."""


DEEP_SYNTHESIZE_SYSTEM = """You are an expert analyst. Synthesize the sub-answers into a comprehensive, well-structured response.

Guidelines:
- Cross-reference findings across sub-answers for consistency
- Organize the response logically (not by sub-question)
- Highlight key insights and connections between findings
- Be thorough but clear — avoid redundancy
- Use appropriate formatting (headers, bullet points) when helpful"""


DEEP_VERIFY_SYSTEM = """You are a critical reviewer. Examine the draft answer and check for:
1. Factual consistency across all sections
2. Missing information or gaps that should be addressed
3. Contradictions with provided source material
4. Completeness relative to the original question
5. Clarity and coherence of the response

If issues are found, fix them and produce the improved final answer.
If the draft is solid, return it with minor polish.
Output ONLY the final refined answer — no meta-commentary about your review process."""


def build_decompose_prompt(
    query: str,
    chat_history: list[dict] | None = None,
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": DEEP_DECOMPOSE_SYSTEM}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})
    return messages


def build_sub_answer_prompt(
    sub_question: str,
    context: str,
    datetime_info: str | None = None,
) -> list[dict[str, str]]:
    system = DEEP_SUB_ANSWER_SYSTEM
    if datetime_info:
        system += f"\n\nCurrent date/time: {datetime_info}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Sub-question: {sub_question}\n\nContext:\n{context}"},
    ]


def build_synthesize_prompt(
    query: str,
    sub_answers: list[dict[str, str]],
    datetime_info: str | None = None,
) -> list[dict[str, str]]:
    system = DEEP_SYNTHESIZE_SYSTEM
    if datetime_info:
        system += f"\n\nCurrent date/time: {datetime_info}"

    sub_text = "\n\n".join(
        f"--- Sub-question {sa['id']}: {sa['question']} ---\n{sa['answer']}"
        for sa in sub_answers
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Original question: {query}\n\nSub-answers:\n{sub_text}"},
    ]


def build_verify_prompt(
    query: str,
    draft: str,
    sources: str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": DEEP_VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question: {query}\n\n"
                f"Draft answer:\n{draft}\n\n"
                f"Source material:\n{sources}"
            ),
        },
    ]
