from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime,
    ForeignKey, JSON, Float, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prompt(Base):
    """
    Immutable prompt versions. Every save creates a new row.
    Active flag controls which version is 'current'.
    """
    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_prompt_name_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_variables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="prompt", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Prompt name={self.name!r} version={self.version} active={self.is_active}>"


class Execution(Base):
    """
    Immutable log of every LLM call. Tied to the exact prompt version used.
    """
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    input_vars: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rendered_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="executions")

    def __repr__(self) -> str:
        return f"<Execution id={self.id} prompt_id={self.prompt_id} status={self.status!r}>"