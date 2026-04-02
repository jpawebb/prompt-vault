from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_store, get_executor
from core.store import PromptStore, PromptNotFoundError
from core.executor import AnthropicExecutor
from models.schemas import ExecuteRequest, ExecuteResponse, ExecutionRead

router = APIRouter(prefix="/prompts", tags=["executions"])


@router.post("/{name}/execute", response_model=ExecuteResponse)
async def execute_prompt(
    name: str,
    payload: ExecuteRequest,
    version: int | None = Query(None, description="Specific version; omit for latest active"),
    store: PromptStore = Depends(get_store),
    executor: AnthropicExecutor = Depends(get_executor),
):
    """
    Render and execute a prompt against the Anthropic API.

    The response includes the exact rendered prompt, LLM output, token counts,
    latency, and the prompt version used — so every response is fully traceable.
    """
    try:
        prompt = await store.get(name, version)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    execution = await executor.render_and_execute(
        prompt_id=prompt.id,
        template=prompt.template,
        variables=payload.variables,
        max_tokens=payload.max_tokens,
        system_prompt=payload.system_prompt,
    )

    saved = await store.log_execution(execution)

    if saved.status not in ("success",):
        # Still return 200 with full context — caller can inspect status + error
        pass

    return ExecuteResponse(
        execution_id=saved.id,
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        rendered_prompt=saved.rendered_prompt,
        output=saved.raw_output,
        input_tokens=saved.input_tokens,
        output_tokens=saved.output_tokens,
        latency_ms=saved.latency_ms,
        model=saved.model or "unknown",
        status=saved.status,
    )


@router.get("/{name}/executions", response_model=list[ExecutionRead])
async def list_executions(
    name: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    store: PromptStore = Depends(get_store),
):
    """
    Retrieve execution history for all versions of a named prompt.
    Ordered newest first.
    """
    try:
        # Validate the prompt exists before querying executions
        await store.list_history(name)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return await store.list_executions(name, limit=limit, offset=offset)