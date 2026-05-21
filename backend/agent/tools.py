"""
Huron Agent Tools — Privileged wrappers around Pinecone namespaces.

Every tool validates the caller's namespace_scope BEFORE executing.
The LLM cannot override this — tools reject calls to unauthorized
namespaces regardless of what the agent's reasoning produces.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ALL_DEPT_CODES = [
    "hr", "legal", "finance", "clinical",
    "operations", "it", "marketing", "external",
]


@dataclass
class ToolPermissionError(Exception):
    dept: str
    user_dept: str

    def __str__(self) -> str:
        return (
            f"Access denied: you do not have permission to search the "
            f"'{self.dept}' namespace. Your account is scoped to: {self.user_dept}"
        )


class AgentTools:
    """
    Builds the tool set for an agent run, scoped to a TenantContext.
    All methods are synchronous — callers must use asyncio.to_thread().
    """

    def __init__(self, tenant_context: Any, pinecone_index: str):
        self.ctx = tenant_context
        self.index_name = pinecone_index
        self._pc_index = None

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_index(self):
        if self._pc_index is None:
            from pinecone import Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
            self._pc_index = pc.Index(self.index_name)
        return self._pc_index

    def _embed(self, text: str) -> list[float]:
        """Embed using OpenAI text-embedding-3-small (1536-dim)."""
        from openai import OpenAI
        res = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")).embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )
        return res.data[0].embedding

    def _assert_dept_access(self, dept: str) -> None:
        scope = getattr(self.ctx, "namespace_scope", [])
        if "*" in scope:
            return
        if dept not in scope:
            raise ToolPermissionError(dept=dept, user_dept=self.ctx.dept_id)

    # ── Tool 1: rag_search ───────────────────────────────────────────────

    def rag_search(self, query: str, dept: str, top_k: int = 8) -> dict:
        """
        Search the knowledge base of a specific department.
        Returns top_k relevant chunks with source metadata.
        Raises ToolPermissionError if caller cannot access dept.
        """
        self._assert_dept_access(dept)
        namespace = f"vaultmind-huron-{dept}-general"
        try:
            idx = self._get_index()
            vec = self._embed(query)
            res = idx.query(
                vector=vec,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
            )
            chunks = [
                {
                    "text":   m.metadata.get("text", ""),
                    "score":  round(m.score, 4),
                    "source": m.metadata.get("source", ""),
                    "page":   m.metadata.get("page", None),
                    "dept":   dept,
                }
                for m in res.matches
            ]
            preview = chunks[0]["text"][:300] if chunks else "No results found in this namespace."
            return {
                "dept":      dept,
                "namespace": namespace,
                "chunks":    chunks,
                "count":     len(chunks),
                "preview":   preview,
            }
        except ToolPermissionError:
            raise
        except Exception as e:
            logger.warning("rag_search error dept=%s: %s", dept, e)
            return {"dept": dept, "error": str(e), "chunks": [], "count": 0,
                    "preview": f"Search failed: {e}"}

    # ── Tool 2: multi_dept_search ────────────────────────────────────────

    def multi_dept_search(self, query: str, depts: list[str], top_k: int = 5) -> dict:
        """
        Search multiple departments simultaneously.
        Requires cross_dept_query permission. Validates each dept individually.
        """
        perms = getattr(self.ctx, "permissions", [])
        role  = getattr(self.ctx, "role", "user")
        if "cross_dept_query" not in perms and role not in ("root", "power_user"):
            raise ToolPermissionError(dept=str(depts), user_dept=self.ctx.dept_id)

        results: dict[str, dict] = {}
        for dept in depts:
            try:
                results[dept] = self.rag_search(query, dept, top_k)
            except ToolPermissionError as e:
                results[dept] = {"error": str(e), "chunks": [], "count": 0}
        return {"results": results, "depts_searched": list(results.keys())}

    # ── Tool 3: compare_results ──────────────────────────────────────────

    def compare_results(
        self,
        text_a: str,
        text_b: str,
        label_a: str = "Source A",
        label_b: str = "Source B",
    ) -> dict:
        """
        Structured comparison of two text passages.
        Returns agreements, conflicts, gaps, and a summary.
        """
        from openai import OpenAI
        prompt = (
            f"Compare these two policy excerpts and identify:\n"
            f"1. Points of AGREEMENT\n"
            f"2. Points of CONFLICT (direct contradictions)\n"
            f"3. GAPS (topic covered in one but not the other)\n\n"
            f"{label_a}:\n{text_a[:1500]}\n\n"
            f"{label_b}:\n{text_b[:1500]}\n\n"
            f'Respond with JSON: {{"agreements":[...],"conflicts":[...],"gaps":[...],"summary":"..."}}'
        )
        try:
            res = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")).chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=600,
            )
            return json.loads(res.choices[0].message.content or "{}")
        except Exception as e:
            return {"error": str(e), "agreements": [], "conflicts": [], "gaps": [],
                    "summary": f"Comparison failed: {e}"}

    # ── Tool 4: get_document_list ────────────────────────────────────────

    def get_document_list(self, dept: str) -> dict:
        """List indexed document count in a department namespace."""
        self._assert_dept_access(dept)
        namespace = f"vaultmind-huron-{dept}-general"
        try:
            idx   = self._get_index()
            stats = idx.describe_index_stats()
            ns    = stats.namespaces.get(namespace, {})
            count = getattr(ns, "vector_count", 0)
            return {
                "dept":         dept,
                "namespace":    namespace,
                "vector_count": count,
                "status":       "active" if count > 0 else "empty",
            }
        except Exception as e:
            return {"dept": dept, "error": str(e), "vector_count": 0}

    # ── OpenAI function-calling schema ───────────────────────────────────

    def as_openai_tools(self) -> list[dict]:
        scope = getattr(self.ctx, "namespace_scope", [])
        perms = getattr(self.ctx, "permissions", [])
        role  = getattr(self.ctx, "role", "user")

        # Departments this user can see in the enum
        allowed_depts = ALL_DEPT_CODES if "*" in scope else [d for d in scope if d in ALL_DEPT_CODES]
        if not allowed_depts:
            allowed_depts = ALL_DEPT_CODES

        tools: list[dict] = [
            {
                "type": "function",
                "function": {
                    "name": "rag_search",
                    "description": (
                        f"Search the knowledge base of a specific department. "
                        f"You have access to: {allowed_depts}"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "dept":  {"type": "string", "description": "Department namespace",
                                      "enum": allowed_depts},
                            "top_k": {"type": "integer", "default": 8,
                                      "description": "Number of results (1-15)"},
                        },
                        "required": ["query", "dept"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_document_list",
                    "description": "Check what documents are indexed in a department namespace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dept": {"type": "string", "enum": allowed_depts},
                        },
                        "required": ["dept"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "compare_results",
                    "description": "Compare two text passages for agreements, conflicts, and gaps",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text_a":  {"type": "string", "description": "First passage"},
                            "text_b":  {"type": "string", "description": "Second passage"},
                            "label_a": {"type": "string", "description": "Label for first passage"},
                            "label_b": {"type": "string", "description": "Label for second passage"},
                        },
                        "required": ["text_a", "text_b"],
                    },
                },
            },
        ]

        # multi_dept_search only for root / power_user / cross_dept_query holders
        if "cross_dept_query" in perms or role in ("root", "power_user"):
            tools.insert(
                1,
                {
                    "type": "function",
                    "function": {
                        "name": "multi_dept_search",
                        "description": "Search multiple departments simultaneously (requires elevated access)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query":  {"type": "string"},
                                "depts":  {"type": "array", "items": {"type": "string"},
                                           "description": "List of department codes to search"},
                                "top_k":  {"type": "integer", "default": 5},
                            },
                            "required": ["query", "depts"],
                        },
                    },
                },
            )

        return tools
