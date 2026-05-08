"""LLM orchestration via the Claude Agent SDK.

The SDK runs the tool-use loop for us. We:
  1. Retrieve top-K chunks from the vector store
  2. Build a user message that contains the question + retrieved chunks
  3. Register a `run_python` MCP tool that wraps our local sandbox
  4. Stream messages from query() until the ResultMessage arrives

The figure produced by run_python and the per-call (code, stdout, error) trail
are captured via a closure dict — the SDK only marshals JSON-serializable tool
results back through the message stream, so arbitrary Python objects (like a
matplotlib Figure) need a side channel.

Streamlit and the eval harness are sync, so `ask()` is a thin sync wrapper
around the async core via `asyncio.run`.
"""

from __future__ import annotations

import asyncio
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
from .prompts import SYSTEM_PROMPT, build_user_message
from .retrieve import retrieve
from .tools import (
    RUN_PYTHON_DESCRIPTION,
    RUN_PYTHON_INPUT_SCHEMA,
    CodeResult,
    run_python as sandbox_run_python,
)


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


def _make_run_python_tool(captured: dict):
    """Build the @tool-decorated callable, closed over `captured` for side-channel state."""

    @tool("run_python", RUN_PYTHON_DESCRIPTION, RUN_PYTHON_INPUT_SCHEMA)
    async def run_python_tool(args: dict[str, Any]) -> dict[str, Any]:
        code = args["code"]
        # The sandbox is sync and CPU-bound; offload so we don't block the event loop.
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


async def _ask_async(question: str, filing_id: str, *, enable_tool: bool) -> AgentResponse:
    chunks = retrieve(filing_id, question)
    user_message = build_user_message(question, chunks)

    captured: dict = {"figure": None, "tool_calls": []}

    if enable_tool:
        server = create_sdk_mcp_server(
            name="askedgar",
            version="1.0.0",
            tools=[_make_run_python_tool(captured)],
        )
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL,
            mcp_servers={"askedgar": server},
            allowed_tools=["mcp__askedgar__run_python"],
            permission_mode="bypassPermissions",
        )
    else:
        # RAG-only baseline: no tools at all
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=config.MODEL,
            allowed_tools=[],
            permission_mode="bypassPermissions",
        )

    final_text = ""
    usage: dict = {}
    async for msg in query(prompt=user_message, options=options):
        if isinstance(msg, AssistantMessage):
            # Stream text from the assistant turn (final-answer text accumulates here too).
            for block in msg.content:
                text = getattr(block, "text", None)
                if text:
                    final_text = text
        elif isinstance(msg, ResultMessage):
            # ResultMessage typically carries the final result + usage.
            result_text = getattr(msg, "result", None)
            if result_text:
                final_text = result_text
            usage = getattr(msg, "usage", None) or {}

    return AgentResponse(
        answer=(final_text or "").strip(),
        chunks=chunks,
        tool_calls=captured["tool_calls"],
        figure=captured["figure"],
        usage=usage,
    )


def ask(question: str, filing_id: str, *, enable_tool: bool = True) -> AgentResponse:
    """Sync entrypoint. enable_tool=False is the RAG-only baseline."""
    return asyncio.run(_ask_async(question, filing_id, enable_tool=enable_tool))
