"""
Microsoft Teams Bot — Bot Framework Emulator / production webhook
=================================================================
  Local demo → test with Bot Framework Emulator (no Teams tenant needed)
  Production → register bot in Azure Bot Service, set MS_APP_ID + MS_APP_SECRET

POST /api/v1/teams/messages  — Activity endpoint (Bot Framework)
GET  /api/v1/teams/health    — Liveness probe for bot registration

The bot forwards user text to the Huron chat API and returns the answer
as an Adaptive Card with source citations.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

_APP_ID     = os.getenv("TEAMS_APP_ID", "")
_APP_SECRET = os.getenv("TEAMS_APP_SECRET", "")
_HURON_API  = os.getenv("HURON_INTERNAL_API", "http://localhost:8004")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bot_auth_token() -> str:
    """Obtain a Bot Framework bearer token using client-credentials flow."""
    r = httpx.post(
        "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     _APP_ID,
            "client_secret": _APP_SECRET,
            "scope":         "https://api.botframework.com/.default",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _build_adaptive_card(answer: str, sources: list[dict]) -> dict:
    """Return a Bot Framework Activity payload wrapping an Adaptive Card."""
    facts = [
        {"title": s.get("filename", s.get("doc_id", "Source")),
         "value": s.get("score", "")}
        for s in sources[:5]
    ]
    card_body: list[dict] = [
        {"type": "TextBlock", "text": answer, "wrap": True, "size": "Medium"},
    ]
    if facts:
        card_body.append({
            "type": "FactSet",
            "facts": facts,
        })
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type":    "AdaptiveCard",
                "version": "1.4",
                "body":    card_body,
            },
        }],
    }


async def _call_huron_chat(
    question: str,
    user_email: str,
    dept: str = "company",
) -> dict[str, Any]:
    """
    Call the Huron internal chat endpoint.
    In demo/emulator mode this can fail gracefully — return a stub answer.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{_HURON_API}/api/v1/chat/query",
                json={
                    "question": question,
                    "dept_id":  dept,
                    "username": user_email,
                },
            )
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("Huron chat API unavailable: %s — returning stub", exc)
        return {
            "answer":  f"(Demo mode) Huron received: "{question}". "
                       "Connect to a live Huron backend for real answers.",
            "sources": [],
        }


async def _send_reply(
    service_url: str,
    conversation_id: str,
    activity_id: str,
    reply_activity: dict,
) -> None:
    """POST a reply back to the Bot Framework service URL."""
    if not _APP_ID:
        # Emulator mode: no auth token needed
        headers = {"Content-Type": "application/json"}
    else:
        token   = _bot_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
    url = f"{service_url.rstrip('/')}/v3/conversations/{conversation_id}/activities/{activity_id}"
    async with httpx.AsyncClient(timeout=20) as client:
        await client.post(url, json=reply_activity, headers=headers)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def teams_health():
    return {"status": "ok", "bot_configured": bool(_APP_ID)}


@router.post("/messages")
async def teams_messages(request: Request):
    """
    Main Bot Framework activity endpoint.
    Handles messageType activities; echoes back via Adaptive Card.
    """
    body: dict = await request.json()

    activity_type = body.get("type", "")
    if activity_type == "conversationUpdate":
        # Bot added to conversation — send greeting
        return Response(status_code=200)

    if activity_type != "message":
        return Response(status_code=200)

    text          = (body.get("text") or "").strip()
    service_url   = body.get("serviceUrl", "")
    conversation  = (body.get("conversation") or {}).get("id", "")
    activity_id   = body.get("id", "")
    from_obj      = body.get("from", {})
    user_email    = from_obj.get("aadObjectId", from_obj.get("id", "teams-user"))

    if not text:
        return Response(status_code=200)

    # Query Huron
    result  = await _call_huron_chat(
        question=text,
        user_email=user_email,
    )
    answer  = result.get("answer", "I could not find an answer.")
    sources = result.get("sources", [])

    reply = _build_adaptive_card(answer, sources)
    reply.update({
        "replyToId":    activity_id,
        "conversation": body.get("conversation", {}),
        "from":         body.get("recipient", {}),
        "recipient":    body.get("from", {}),
        "locale":       body.get("locale", "en-US"),
    })

    try:
        await _send_reply(service_url, conversation, activity_id, reply)
    except Exception as exc:
        logger.warning("Could not send Teams reply: %s", exc)

    return Response(status_code=200)
