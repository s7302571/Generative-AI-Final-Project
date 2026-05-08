"""LLM orchestration via the Claude Agent SDK.

Two modes, picked by whether `store` is None:

  - No store: plain chat. The user's question goes straight to the model with
    a general-assistant system prompt and no tools.
  - With store: RAG. We retrieve top-K chunks, inject them into the user
    message, and register a `run_python` MCP tool so the model can compute
    exact numbers / render charts.

The figure produced by run_python and the per-call (code, stdout, error) trail
are captured via a closure dict — the SDK only marshals JSON-serializable tool
results, so arbitrary Python objects (a matplotlib Figure) need a side channel.

Streamlit and the eval harness are sync, so `ask()` is a thin sync wrapper
around the async core via `asyncio.run`.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from . import config
from .prompts import (
    FILING_SYSTEM_PROMPT,
    GENERAL_SYSTEM_PROMPT,
    build_filing_user_message,
)
from .tools import (
    RUN_PYTHON_DESCRIPTION,
    RUN_PYTHON_INPUT_SCHEMA,
    CodeResult,
    run_python as sandbox_run_python,
)
from .vectorstore import VectorStore


@dataclass
class ToolCall:
    code: str
    result: CodeResult


@dataclass
class AgentResponse:
    answer: str
    chunks: list[dict] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    figure: Any | None = None
    usage: dict = field(default_factory=dict)
    structured_answer: dict | None = None


_ANSWER_JSON_RE = re.compile(
    r"<answer_json>\s*(.*?)\s*</answer_json>",
    re.DOTALL | re.IGNORECASE,
)


def _split_answer(text: str) -> tuple[str, dict | None]:
    """Pull the <answer_json>{...}</answer_json> block out of the model's reply.

    Returns (prose_answer_with_tag_stripped, parsed_json_or_None). If the model
    forgot the tag or the JSON is malformed, structured_answer is None and the
    grader will fall back to regex/judge.
    """
    match = _ANSWER_JSON_RE.search(text)
    if not match:
        return text, None
    raw = match.group(1).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return text, None
    if not isinstance(parsed, dict):
        return text, None
    cleaned = _ANSWER_JSON_RE.sub("", text).rstrip()
    return cleaned, parsed


def _make_run_python_tool(captured: dict):
    @tool("run_python", RUN_PYTHON_DESCRIPTION, RUN_PYTHON_INPUT_SCHEMA)
    async def run_python_tool(args: dict[str, Any]) -> dict[str, Any]:
        code = args["code"]
        result = await asyncio.to_thread(sandbox_run_python, code)
        captured["tool_calls"].append(ToolCall(code=code, result=result))
        if result.figure is not None and captured["figure"] is None:
            captured["figure"] = result.figure
        text = (
            result.stdout if result.ok
            else f"ERROR:\n{result.error}\nstdout:\n{result.stdout}"
        )
        return {
            "content": [{"type": "text", "text": text or "(no stdout)"}],
            "is_error": not result.ok,
        }

    return run_python_tool


async def _ask_async(
    question: str,
    *,
    store: VectorStore | None,
    enable_tool: bool,
    expected_keys: list[str] | None = None,
) -> AgentResponse:
    captured: dict = {"figure": None, "tool_calls": []}

    if store is not None:
        chunks = store.query(question)
        prompt = build_filing_user_message(question, chunks, expected_keys=expected_keys)
        if enable_tool:
            server = create_sdk_mcp_server(
                name="askedgar",
                version="1.0.0",
                tools=[_make_run_python_tool(captured)],
            )
            options = ClaudeAgentOptions(
                system_prompt=FILING_SYSTEM_PROMPT,
                model=config.MODEL,
                mcp_servers={"askedgar": server},
                allowed_tools=["mcp__askedgar__run_python"],
                permission_mode="bypassPermissions",
            )
        else:
            options = ClaudeAgentOptions(
                system_prompt=FILING_SYSTEM_PROMPT,
                model=config.MODEL,
                allowed_tools=[],
                permission_mode="bypassPermissions",
            )
    else:
        chunks = []
        prompt = question
        options = ClaudeAgentOptions(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            model=config.MODEL,
            allowed_tools=[],
            permission_mode="bypassPermissions",
        )

    final_text = ""
    usage: dict = {}
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                text = getattr(block, "text", None)
                if text:
                    final_text = text
        elif isinstance(msg, ResultMessage):
            result_text = getattr(msg, "result", None)
            if result_text:
                final_text = result_text
            usage = getattr(msg, "usage", None) or {}

    prose, structured = _split_answer((final_text or "").strip())
    return AgentResponse(
        answer=prose,
        chunks=chunks,
        tool_calls=captured["tool_calls"],
        figure=captured["figure"],
        usage=usage,
        structured_answer=structured,
    )


def ask(
    question: str,
    *,
    store: VectorStore | None = None,
    enable_tool: bool = True,
    expected_keys: list[str] | None = None,
) -> AgentResponse:
    """Sync entrypoint.

    - store=None: plain chat, no retrieval, no tool.
    - store given, enable_tool=True: RAG + run_python (full system).
    - store given, enable_tool=False: RAG only, no tool (eval baseline).
    - expected_keys: when set, the user message instructs the model to use
      these exact snake_case keys in its <answer_json> block. Used by the eval
      harness to keep model output aligned with the grader's schema.
    """
    return asyncio.run(
        _ask_async(question, store=store, enable_tool=enable_tool, expected_keys=expected_keys)
    )
