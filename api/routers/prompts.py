from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from api.dependencies import get_store, get_renderer
from core.store import PromptStore, PromptNotFoundError
from core.renderer import PromptRenderer, PromptRenderError
from models.schemas import (
    PromptCreate,
    PromptRead,
    PromptSummary,
    PromptDiff,
    RenderRequest,
    RenderResponse,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("/", response_model=PromptRead, status_code=201)
async def create_prompt(
    payload: PromptCreate,
    renderer: PromptRenderer = Depends(get_renderer),
    store: PromptStore = Depends(get_store),
):
    """
    Register a new prompt (or a new version of an existing prompt).
    Template syntax is validated before persisting.
    """
    try:
        renderer.validate_template(payload.template)
    except PromptRenderError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        prompt = await store.create(payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Prompt version conflict.")

    return prompt


@router.get("/", response_model=list[PromptSummary])
async def list_prompts(
    tag: str | None = Query(None, description="Filter by tag"),
    active_only: bool = Query(False, description="Return only active versions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    store: PromptStore = Depends(get_store),
):
    """List all prompts with optional tag and active filters."""
    return await store.list_all(tag=tag, active_only=active_only, limit=limit, offset=offset)


@router.get("/{name}", response_model=PromptRead)
async def get_prompt(
    name: str,
    version: int | None = Query(None, description="Specific version; omit for latest active"),
    store: PromptStore = Depends(get_store),
):
    """Fetch a prompt by name. Defaults to latest active version."""
    try:
        return await store.get(name, version)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/history", response_model=list[PromptRead])
async def get_prompt_history(
    name: str,
    store: PromptStore = Depends(get_store),
):
    """List all versions of a prompt, newest first."""
    try:
        return await store.list_history(name)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/diff", response_model=PromptDiff)
async def diff_prompt_versions(
    name: str,
    version_a: int = Query(..., description="Base version"),
    version_b: int = Query(..., description="Target version"),
    store: PromptStore = Depends(get_store),
):
    """Unified diff between two versions of a prompt template."""
    try:
        return await store.diff(name, version_a, version_b)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/rollback", response_model=PromptRead)
async def rollback_prompt(
    name: str,
    version: int = Query(..., description="Version to roll back to"),
    store: PromptStore = Depends(get_store),
):
    """Activate a prior version. Does not delete or mutate existing rows."""
    try:
        return await store.rollback(name, version)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/render", response_model=RenderResponse)
async def render_prompt(
    name: str,
    payload: RenderRequest,
    version: int | None = Query(None),
    renderer: PromptRenderer = Depends(get_renderer),
    store: PromptStore = Depends(get_store),
):
    """
    Render a prompt template with provided variables — without calling the LLM.
    Useful for previewing output before execution.
    """
    try:
        prompt = await store.get(name, version)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        rendered = renderer.render(prompt.template, payload.variables)
    except PromptRenderError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return RenderResponse(name=prompt.name, version=prompt.version, rendered=rendered)