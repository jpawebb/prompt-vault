from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from core.renderer import PromptRenderer, renderer
from core.store import PromptStore
from core.executor import AnthropicExecutor


def get_renderer() -> PromptRenderer:
    return renderer


def get_store(db: AsyncSession = Depends(get_db)) -> PromptStore:
    return PromptStore(db)


def get_executor(r: PromptRenderer = Depends(get_renderer)) -> AnthropicExecutor:
    return AnthropicExecutor(renderer=r)