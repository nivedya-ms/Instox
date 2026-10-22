"""Two-hop pipeline: question → SQL → rows → natural-language answer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .llm import LLMClient, LLMError, StubLLM
from .sql_sandbox import (
    SCHEMA_DESCRIPTION,
    SqlResult,
    is_safe_readonly_sql,
    run_scoped_query,
)


@dataclass
class ChatResult:
    question: str
    answer: str
    sql: Optional[str] = None
    result: Optional[SqlResult] = None
    error: Optional[str] = None
    used_stub: bool = False

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sql": self.sql,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "used_stub": self.used_stub,
        }


_STUB_UNKNOWN_MESSAGE = (
    "The AI chat is running in stub mode — it only understands a few example "
    "questions right now. Try: \"How much profit today?\", \"What's my best selling "
    "product?\", \"Which items are low stock?\", or \"How much did I make this month?\". "
    "Add DEEPSEEK_API_KEY to your .env and set LLM_PROVIDER=deepseek to enable real AI."
)


def _extract_sql(text: str) -> Optional[str]:
    """Pull the first SQL statement out of the model's response.

    Models often wrap SQL in ```sql fences or add a leading 'Here's the SQL:'.
    We tolerate both.
    """
    if not text:
        return None
    fenced = re.search(r"```(?:sql)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    # Otherwise treat the first line that starts with SELECT/WITH as the query.
    lines = text.strip().splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*(select|with)\b", line, re.IGNORECASE):
            return "\n".join(lines[i:]).strip()
    return text.strip() or None


def answer_question(
    question: str,
    user_id: int,
    db_path: str,
    llm: LLMClient,
    max_rows: int = 100,
    timeout_ms: int = 3000,
) -> ChatResult:
    """Run the full NL→SQL→answer pipeline.

    Never raises for expected error modes (LLM failure, unsafe SQL, execution
    error) — surfaces them via `ChatResult.error` with a user-friendly answer.
    Unexpected exceptions propagate.
    """
    question = (question or "").strip()
    if not question:
        return ChatResult(question=question, answer="Ask me a question about your shop.")

    used_stub = isinstance(llm, StubLLM)

    # --- Hop 1: question → SQL --------------------------------------------
    sql_messages = [
        {
            "role": "system",
            "content": "You are a SQL assistant.\n" + SCHEMA_DESCRIPTION,
        },
        {"role": "user", "content": question},
    ]
    try:
        raw = llm.complete(sql_messages, temperature=0.0, max_tokens=350)
    except LLMError as e:
        return ChatResult(
            question=question,
            answer="I couldn't reach the AI service. Try again in a moment.",
            error=str(e),
            used_stub=used_stub,
        )

    sql = _extract_sql(raw)
    if not sql or "STUB" in sql:
        return ChatResult(
            question=question,
            answer=_STUB_UNKNOWN_MESSAGE if used_stub else "I couldn't turn that into a query.",
            used_stub=used_stub,
        )

    ok, reason = is_safe_readonly_sql(sql)
    if not ok:
        return ChatResult(
            question=question,
            answer="I generated an unsafe query, so I refused to run it. Try rephrasing.",
            sql=sql,
            error=reason,
            used_stub=used_stub,
        )

    # --- Execute ----------------------------------------------------------
    try:
        result = run_scoped_query(
            db_path=db_path,
            user_id=user_id,
            sql=sql,
            max_rows=max_rows,
            timeout_ms=timeout_ms,
        )
    except ValueError as e:
        return ChatResult(
            question=question,
            answer="I couldn't run that query against your data. Try rephrasing.",
            sql=sql,
            error=str(e),
            used_stub=used_stub,
        )

    # --- Hop 2: rows → natural-language answer ----------------------------
    answer_messages = [
        {
            "role": "system",
            "content": (
                "You explain shop data results to a small shop owner in India. "
                "Answer in one or two short sentences. Use ₹ for money and include "
                "the actual numbers from the result. Do not mention SQL."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n"
                f"Result:\n{result.as_text_table()}\n"
                "Reply with the answer only."
            ),
        },
    ]
    try:
        answer = llm.complete(answer_messages, temperature=0.2, max_tokens=200)
    except LLMError as e:
        # Fall back to a raw dump of the numbers.
        answer = _fallback_answer(result)
        return ChatResult(
            question=question,
            answer=answer,
            sql=sql,
            result=result,
            error=str(e),
            used_stub=used_stub,
        )

    if not answer:
        answer = _fallback_answer(result)

    return ChatResult(
        question=question,
        answer=answer,
        sql=sql,
        result=result,
        used_stub=used_stub,
    )


def _fallback_answer(result: SqlResult) -> str:
    if not result.rows:
        return "No matching data found."
    if len(result.rows) == 1 and len(result.columns) <= 3:
        parts = [
            f"{col.replace('_', ' ')}: {result.rows[0][i]}"
            for i, col in enumerate(result.columns)
        ]
        return "; ".join(parts)
    return f"Found {len(result.rows)} result(s). See details below."
