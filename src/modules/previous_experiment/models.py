from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, BigInteger, Text, Float, Numeric
from src.database.connection import Base

class PreviousExperimentModel(Base):
    __tablename__ = "previous_experiments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"))
    locale_id: Mapped[str] = mapped_column(ForeignKey("locales.id"), nullable=True)
    google_play_experiment_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    name: Mapped[str] = mapped_column(String(600), default="")
    experiment_type: Mapped[str] = mapped_column(String(50), default="")
    store: Mapped[str] = mapped_column(String(50), default="")
    csl: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[datetime] = mapped_column()
    end_date: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)
    result: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(300))
    segmentation: Mapped[str] = mapped_column(String(300), default="")
    installers: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, default=None)
    retained_installers: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, default=None)
    applied: Mapped[bool] = mapped_column(default=False)
    winner: Mapped[bool] = mapped_column(default=False)
    min_detectable_effect: Mapped[Optional[float]] = mapped_column(Float, default=0, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    app = relationship("AppModel", back_populates="previous_experiments")
    locale = relationship("LocaleModel", back_populates="previous_experiments")
    previous_variants: Mapped[List["PreviousVariantModel"]] = relationship(
        "PreviousVariantModel", 
        back_populates="previous_experiment", 
        cascade="all, delete-orphan"
    )



class PreviousVariantModel(Base):
    __tablename__ = "previous_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("previous_experiments.id"))
    name: Mapped[str] = mapped_column(String(255))
    # Asset fields
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    promo_video: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    feature_graphic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Screenshots
    screen1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen6: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen7: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen8: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # 7-inch tablet screenshots
    screen1_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen2_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen3_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen4_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen5_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen6_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen7_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen8_7inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # 10-inch tablet screenshots
    screen1_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen2_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen3_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen4_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen5_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen6_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen7_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    screen8_10inch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metrics fields
    installs: Mapped[int] = mapped_column(Integer)
    installs_scaled: Mapped[int] = mapped_column(Integer)
    audience: Mapped[float] = mapped_column(Numeric(5, 2))  # 5 total digits, 2 decimal places
    performance_start: Mapped[float] = mapped_column(Numeric(7, 5))  # 7 total digits, 5 decimal places
    performance_end: Mapped[float] = mapped_column(Numeric(7, 5))  # 7 total digits, 5 decimal places
    applied: Mapped[bool] = mapped_column(default=False)
    winner: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    previous_experiment = relationship("PreviousExperimentModel", back_populates="previous_variants")