from openai import OpenAI

from app.config import settings


def chat_completion(messages: list[dict], temperature: float = 0.7) -> str | None:
    """Use DeepSeek when configured; return None so deterministic fallback can take over."""
    if not settings.deepseek_api_key:
        return None
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        timeout=30,
    )
    return response.choices[0].message.content or None

