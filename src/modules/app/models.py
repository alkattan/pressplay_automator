from datetime import datetime, timezone
from sqlalchemy import Integer, String, BigInteger, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.connection import Base
from typing import Optional, List
from src.modules.experiment.models import ExperimentModel
from src.modules.csl.models import CSLModel
from src.modules.app.schemas import AppStatus


class AppModel(Base):
    __tablename__ = "apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
    name: Mapped[str] = mapped_column(String(255))
    abbreviation: Mapped[str] = mapped_column(String(50))
    package_id: Mapped[str] = mapped_column(String(255))
    play_console_id: Mapped[str] = mapped_column(String(255))
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[AppStatus] = mapped_column(Enum(AppStatus))
    automated_send_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    automated_publishing: Mapped[bool] = mapped_column(Boolean, default=False)
    reporting: Mapped[bool] = mapped_column(Boolean, default=False)
    automated_testing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    sync_now: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_csls_now: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    next_sync: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    slack_hook_url: Mapped[str] = mapped_column(String(255), nullable=True)
    publisher = relationship("PublisherModel", back_populates="apps")
    csls: Mapped[List["CSLModel"]] = relationship(back_populates="app", cascade="all, delete-orphan")
    experiments: Mapped[List["ExperimentModel"]] = relationship(back_populates="app", cascade="all, delete-orphan")
    publishing_overviews: Mapped[List["PublishingOverviewModel"]] = relationship(back_populates="app", cascade="all, delete-orphan")
