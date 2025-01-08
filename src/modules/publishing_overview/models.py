from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, Boolean, ForeignKey
from src.database.connection import Base

class PublishingOverviewModel(Base):
    __tablename__ = "publishing_overview"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"))
    chnages: Mapped[str] = mapped_column(Text)
    publish_decision: Mapped[bool] = mapped_column(Boolean)
    review_decision: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    app = relationship("AppModel", back_populates="publishing_overviews")