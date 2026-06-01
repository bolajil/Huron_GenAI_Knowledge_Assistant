import requests


def run(config: dict, result_text: str, query: str, user_params: dict) -> dict:
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError(
            "Slack webhook URL is not configured for your department. "
            "Ask an admin to set it under MCP → Manage Tools."
        )
    channel = user_params.get("channel") or config.get("default_channel", "")
    text = f"*Query Result*\n*Question:* {query[:300]}\n\n{result_text[:2800]}"
    payload: dict = {"text": text}
    if channel:
        payload["channel"] = channel

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    return {"detail": f"Sent to {channel or 'default channel'}"}
