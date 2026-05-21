"""
Huron ReAct Agent — OpenAI function-calling loop with SSE step emission.

Each iteration: LLM reasons → calls a tool → observes result → repeats.
Runs inside asyncio.create_task(); yields step dicts consumed by the SSE
endpoint. Tool calls are wrapped in asyncio.to_thread() so blocking I/O
(Pinecone, OpenAI embeddings) never blocks the event loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from .tools import AgentTools, ToolPermissionError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Huron's enterprise knowledge assistant.
You help staff answer complex questions that require searching multiple knowledge bases.

CRITICAL RULES:
1. You can only search departments that your tools explicitly allow.
2. If a tool returns a permission denied error, acknowledge it clearly and work with
   the data you do have access to.
3. Always cite the specific documents or sources you found.
4. If you cannot fully answer due to access restrictions, say so clearly rather than
   fabricating an answer.
5. Never invent information. Only use what you retrieved from the knowledge base.
6. When comparing policies from different departments, use the compare_results tool."""


class ReActAgent:
    def __init__(
        self,
        tenant_context: Any,
        run_id: str,
        max_steps: int = 12,
        model: str = "gpt-4o-mini",
    ):
        self.ctx        = tenant_context
        self.run_id     = run_id
        self.max_steps  = max_steps
        self.model      = model
        self.client     = AsyncOpenAI(api_key=__import__("os").getenv("OPENAI_API_KEY", ""))
        self.tools      = AgentTools(
            tenant_context,
            pinecone_index=__import__("os").getenv("PINECONE_INDEX", "huron-enterprise-knowledge"),
        )
        self.steps: list[dict]  = []
        self._stop_requested    = False

    def stop(self) -> None:
        self._stop_requested = True

    # ── Main loop ───────────────────────────────────────────────────────

    async def run(self, query: str) -> AsyncGenerator[dict, None]:
        """Execute the ReAct loop. Yields step dicts for SSE streaming."""
        messages   = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": query},
        ]
        oai_tools  = self.tools.as_openai_tools()
        step_num   = 0

        while step_num < self.max_steps and not self._stop_requested:
            step_num += 1

            # ── Call LLM ────────────────────────────────────────────────
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=oai_tools,
                    tool_choice="auto",
                )
            except Exception as e:
                err = self._step("error", {"message": str(e)}, step_num)
                self.steps.append(err)
                yield err
                return

            msg = response.choices[0].message

            # ── Pure thought (no tool call) → agent is done ─────────────
            if msg.content and not msg.tool_calls:
                thought = self._step("thought", {"content": msg.content}, step_num)
                self.steps.append(thought)
                yield thought

                messages.append({"role": "assistant", "content": msg.content})

                complete = self._step("complete", {
                    "answer":               msg.content,
                    "steps_taken":          step_num,
                    "namespaces_accessed":  self._namespaces_accessed(),
                    "faithfulness_score":   0.0,
                }, step_num)
                self.steps.append(complete)
                yield complete
                return

            # ── Tool calls ───────────────────────────────────────────────
            if msg.tool_calls:
                messages.append({
                    "role":       "assistant",
                    "content":    msg.content,
                    "tool_calls": [
                        {
                            "id":       tc.id,
                            "type":     "function",
                            "function": {
                                "name":      tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    # Emit tool_call step
                    call_step = self._step("tool_call", {"tool": name, "args": args}, step_num)
                    self.steps.append(call_step)
                    yield call_step

                    # Execute tool in a thread (all tools are sync / blocking I/O)
                    try:
                        tool_fn    = getattr(self.tools, name)
                        result     = await asyncio.to_thread(tool_fn, **args)
                        count      = result.get("count", 0) if isinstance(result, dict) else 0
                        result_step = self._step(
                            "tool_result",
                            {"tool": name, "args": args, "result": result, "count": count},
                            step_num,
                        )
                        result_str = json.dumps(result)[:3000]

                    except ToolPermissionError as e:
                        result_step = self._step(
                            "permission_denied",
                            {"tool": name, "dept": args.get("dept", ""), "reason": str(e)},
                            step_num,
                        )
                        result_str = str(e)

                    except Exception as e:
                        result_step = self._step(
                            "tool_error",
                            {"tool": name, "error": str(e)},
                            step_num,
                        )
                        result_str = f"Tool error: {e}"

                    self.steps.append(result_step)
                    yield result_step

                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      result_str,
                    })

        # ── Max steps reached ────────────────────────────────────────────
        if step_num >= self.max_steps and not self._stop_requested:
            max_step = self._step("max_steps", {
                "message":     f"Reached maximum steps ({self.max_steps}). Generating best answer.",
                "steps_taken": step_num,
            }, step_num)
            self.steps.append(max_step)
            yield max_step

            # One final call without tools to force a summary
            messages.append({"role": "user", "content": "Summarize what you found so far."})
            try:
                final  = await self.client.chat.completions.create(
                    model=self.model, messages=messages
                )
                answer = final.choices[0].message.content or ""
            except Exception:
                answer = "Unable to generate final answer."

            complete = self._step("complete", {
                "answer":              answer,
                "steps_taken":         step_num,
                "namespaces_accessed": self._namespaces_accessed(),
                "truncated":           True,
            }, step_num)
            self.steps.append(complete)
            yield complete

    # ── Helpers ─────────────────────────────────────────────────────────

    def _step(self, step_type: str, data: dict, step_num: int) -> dict:
        return {
            "run_id":    self.run_id,
            "step_num":  step_num,
            "type":      step_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }

    def _namespaces_accessed(self) -> list[str]:
        accessed: set[str] = set()
        for s in self.steps:
            if s.get("type") == "tool_result":
                dept = (s.get("args") or {}).get("dept", "")
                if dept:
                    accessed.add(dept)
            elif s.get("type") == "tool_call":
                # multi_dept_search passes depts list
                depts = (s.get("args") or {}).get("depts", [])
                for d in depts:
                    accessed.add(d)
        return sorted(accessed)
