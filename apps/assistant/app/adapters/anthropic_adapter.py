"""Anthropic adapter (T-201). Использует anthropic SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm_base import BaseLLMAdapter, LLMRequest, LLMResponse


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Messages API."""

    def __init__(self, model_id: str, api_key: str | None, base_url: str | None):
        super().__init__(model_id, api_key, base_url)
        # Lazy import — anthropic может быть не установлен
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("anthropic SDK не установлен. Установи: uv add anthropic") from e
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        msg = await self.client.messages.create(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt or "",
            messages=[{"role": "user", "content": request.prompt}],
        )
        content = "".join(block.text for block in msg.content if hasattr(block, "text"))
        return LLMResponse(
            content=content,
            model=msg.model,
            usage={
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
            },
            raw=msg,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt or "",
            messages=[{"role": "user", "content": request.prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
