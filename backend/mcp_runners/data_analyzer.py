import os


def run(config: dict, result_text: str, query: str, user_params: dict) -> dict:
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    focus   = user_params.get("analysis_type") or "trends, patterns, and key insights"
    client  = openai.OpenAI(api_key=api_key)
    prompt  = (
        f"You are a data analyst. Analyze the content below and identify {focus}. "
        "Be concise and structured."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",  "content": prompt},
            {"role": "user",    "content": f"Original query: {query}\n\nContent:\n{result_text[:4000]}"},
        ],
        max_tokens=1500,
    )
    analysis = resp.choices[0].message.content or ""
    return {"detail": "Analysis complete", "analysis": analysis}
