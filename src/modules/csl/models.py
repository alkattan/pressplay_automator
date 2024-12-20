from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Enum
from src.database.connection import Base
from sqlalchemy import UniqueConstraint
from src.db_associations import csl_locale
from src.modules.csl.schemas import CSLLocaleStatus




class CSLModel(Base):
    __tablename__ = "csls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"))
    name: Mapped[str] = mapped_column(String(255))
    play_console_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    app = relationship("AppModel", back_populates="csls")
    locales = relationship("LocaleModel", secondary=csl_locale, back_populates="csls")

class LocaleModel(Base):
    __tablename__ = "locales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    status: Mapped[CSLLocaleStatus] = mapped_column(Enum(CSLLocaleStatus), default=CSLLocaleStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    csls = relationship("CSLModel", secondary=csl_locale, back_populates="locales") 