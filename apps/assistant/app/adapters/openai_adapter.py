"""OpenAI adapter (T-201). Использует openai SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm_base import BaseLLMAdapter, LLMRequest, LLMResponse


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI Chat Completions API."""

    def __init__(self, model_id: str, api_key: str | None, base_url: str | None):
        super().__init__(model_id, api_key, base_url)
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError("openai SDK не установлен. Установи: uv add openai") from e
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        resp = await self.client.chat.completions.create(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
        )
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=resp.model,
            usage={
                "input_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "output_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            raw=resp,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        stream = await self.client.chat.completions.create(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
