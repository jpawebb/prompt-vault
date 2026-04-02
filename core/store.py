import difflib
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Prompt, Execution
from models.schemas import PromptCreate, PromptDiff
from core.renderer import renderer


class PromptNotFoundError(Exception):
    pass


class PromptStore:
    """
    Repository layer for Prompt persistence.

    Versioning contract:
    - Every save is an INSERT — templates are never mutated.
    - `version` auto-increments per prompt name.
    - Only one version is `is_active=True` per name at any time.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: PromptCreate) -> Prompt:
        """
        Create a new versioned prompt. Deactivates prior active version.
        """
        # Determine next version number
        result = await self.db.execute(
            select(func.max(Prompt.version)).where(Prompt.name == data.name)
        )
        max_version: int | None = result.scalar()
        next_version = (max_version or 0) + 1

        # Deactivate current active version (if any)
        if max_version is not None:
            await self.db.execute(
                update(Prompt)
                .where(Prompt.name == data.name, Prompt.is_active.is_(True))
                .values(is_active=False)
            )

        # Extract variables from template
        input_variables = renderer.extract_variables(data.template)

        prompt = Prompt(
            name=data.name,
            description=data.description,
            template=data.template,
            version=next_version,
            tags=data.tags,
            is_active=True,
            input_variables=input_variables,
        )
        self.db.add(prompt)
        await self.db.flush()
        await self.db.refresh(prompt)
        return prompt

    async def get_latest(self, name: str) -> Prompt:
        """Fetch the currently active version for a prompt name."""
        result = await self.db.execute(
            select(Prompt)
            .where(Prompt.name == name, Prompt.is_active.is_(True))
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise PromptNotFoundError(f"No active prompt found with name={name!r}")
        return prompt

    async def get_version(self, name: str, version: int) -> Prompt:
        """Fetch a specific version of a prompt."""
        result = await self.db.execute(
            select(Prompt).where(Prompt.name == name, Prompt.version == version)
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise PromptNotFoundError(
                f"Prompt name={name!r} version={version} not found"
            )
        return prompt

    async def get(self, name: str, version: int | None = None) -> Prompt:
        """Resolve a prompt by name and optional version (defaults to latest active)."""
        if version is not None:
            return await self.get_version(name, version)
        return await self.get_latest(name)

    async def list_all(
        self,
        tag: str | None = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Prompt]:
        """List prompts with optional tag filter and active filter."""
        query = select(Prompt)
        if active_only:
            query = query.where(Prompt.is_active.is_(True))
        if tag:
            query = query.where(Prompt.tags.contains([tag]))
        query = query.order_by(Prompt.name, Prompt.version.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_history(self, name: str) -> list[Prompt]:
        """All versions for a given prompt name, newest first."""
        result = await self.db.execute(
            select(Prompt)
            .where(Prompt.name == name)
            .order_by(Prompt.version.desc())
        )
        versions = list(result.scalars().all())
        if not versions:
            raise PromptNotFoundError(f"No prompt found with name={name!r}")
        return versions

    async def rollback(self, name: str, version: int) -> Prompt:
        """
        Set a prior version as active. Deactivates current active version.
        Does NOT create a new version row — rollback is a pointer change.
        """
        target = await self.get_version(name, version)

        await self.db.execute(
            update(Prompt)
            .where(Prompt.name == name, Prompt.is_active.is_(True))
            .values(is_active=False)
        )
        await self.db.execute(
            update(Prompt)
            .where(Prompt.id == target.id)
            .values(is_active=True)
        )
        await self.db.refresh(target)
        return target

    async def diff(self, name: str, version_a: int, version_b: int) -> PromptDiff:
        """Line-level diff between two versions of a prompt template."""
        a = await self.get_version(name, version_a)
        b = await self.get_version(name, version_b)

        diff_lines = list(
            difflib.unified_diff(
                a.template.splitlines(keepends=True),
                b.template.splitlines(keepends=True),
                fromfile=f"{name} v{version_a}",
                tofile=f"{name} v{version_b}",
            )
        )
        return PromptDiff(
            name=name,
            version_a=version_a,
            version_b=version_b,
            diff_lines=diff_lines,
        )

    async def log_execution(self, execution: Execution) -> Execution:
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def list_executions(
        self, prompt_name: str, limit: int = 50, offset: int = 0
    ) -> list[Execution]:
        """Fetch execution history for all versions of a named prompt."""
        result = await self.db.execute(
            select(Execution)
            .join(Prompt, Execution.prompt_id == Prompt.id)
            .where(Prompt.name == prompt_name)
            .order_by(Execution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())