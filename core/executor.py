import time
import logging
from typing import Any

import anthropic

from core.config import get_settings
from core.renderer import PromptRenderer, PromptRenderError
from db.models import Execution

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionError(Exception):
    pass


class AnthropicExecutor:
    """
    Renders a prompt template and executes it against the Anthropic API.

    Every call produces an Execution record capturing:
    - The exact rendered prompt
    - Input variables used
    - Raw output text
    - Token counts (input + output)
    - Latency in milliseconds
    - Model used
    - Status (success | error) + error message if applicable

    This ensures every LLM response is fully traceable back to the exact
    prompt version that generated it.
    """

    def __init__(self, renderer: PromptRenderer):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._renderer = renderer
        self._model = settings.anthropic_model

    async def render_and_execute(
        self,
        prompt_id: int,
        template: str,
        variables: dict[str, Any],
        max_tokens: int = 1024,
        system_prompt: str | None = None,
    ) -> Execution:
        """
        Render the template, call the Anthropic API, and return a populated
        Execution ORM object (not yet persisted — caller handles commit).
        """
        # Step 1: Render
        try:
            rendered = self._renderer.render(template, variables)
        except PromptRenderError as e:
            return Execution(
                prompt_id=prompt_id,
                input_vars=variables,
                rendered_prompt=template,
                status="render_error",
                error=str(e),
            )

        # Step 2: Call Anthropic
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": rendered}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        start = time.monotonic()
        try:
            response = await self._client.messages.create(**kwargs)
            latency_ms = (time.monotonic() - start) * 1000

            output_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

            logger.info(
                "Execution success | prompt_id=%s model=%s input_tokens=%s output_tokens=%s latency_ms=%.1f",
                prompt_id,
                self._model,
                response.usage.input_tokens,
                response.usage.output_tokens,
                latency_ms,
            )

            return Execution(
                prompt_id=prompt_id,
                input_vars=variables,
                rendered_prompt=rendered,
                raw_output=output_text,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=round(latency_ms, 2),
                model=self._model,
                status="success",
            )

        except anthropic.APIStatusError as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("Anthropic API error | status=%s body=%s", e.status_code, e.message)
            return Execution(
                prompt_id=prompt_id,
                input_vars=variables,
                rendered_prompt=rendered,
                latency_ms=round(latency_ms, 2),
                model=self._model,
                status="api_error",
                error=f"HTTP {e.status_code}: {e.message}",
            )
        except anthropic.APIConnectionError as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("Anthropic connection error | %s", str(e))
            return Execution(
                prompt_id=prompt_id,
                input_vars=variables,
                rendered_prompt=rendered,
                latency_ms=round(latency_ms, 2),
                model=self._model,
                status="connection_error",
                error=str(e),
            )