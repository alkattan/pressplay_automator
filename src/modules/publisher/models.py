from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Integer, String, BigInteger, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.connection import Base
from typing import Optional
from src.modules.publisher.schemas import PublisherStatus
from src.modules.organization.models import OrganizationModel

class PublisherModel(Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    link_code: Mapped[str] = mapped_column(String(255))
    status: Mapped[PublisherStatus] = mapped_column(SQLEnum(PublisherStatus))
    play_console_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    dataset: Mapped[str] = mapped_column(String(255))
    slack_hook_url: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    organization = relationship("OrganizationModel", back_populates="publishers")
    apps = relationship("AppModel", back_populates="publisher") 