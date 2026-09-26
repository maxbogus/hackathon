"""LiteLLM adapter (T-201). Использует litellm как proxy для разных провайдеров."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm_base import BaseLLMAdapter, LLMRequest, LLMResponse


class LiteLLMAdapter(BaseLLMAdapter):
    """LiteLLM proxy (OpenRouter, GigaChat, DeepSeek, и др.)."""

    def __init__(self, model_id: str, api_key: str | None, base_url: str | None):
        super().__init__(model_id, api_key, base_url)
        try:
            import litellm
        except ImportError as e:
            raise ImportError(
                "litellm не установлен. Установи: uv add litellm"
            ) from e
        self.litellm = litellm
        self.litellm.api_base = base_url
        self.litellm.api_key = api_key

    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        resp = await self.litellm.acompletion(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
        )
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=resp.model,
            usage=dict(resp.usage) if resp.usage else {},
            raw=resp,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        resp = await self.litellm.acompletion(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
            stream=True,
        )
        async for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
