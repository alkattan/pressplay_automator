from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.connection import Base
from sqlalchemy import String, Integer, Enum, ForeignKey, Float, Text
from src.modules.experiment.schemas import ApplySetting, ApplyOnPercentile, MinimumDetectableEffectEnum, ConfidenceIntervalEnum, TargetMetric
from src.modules.experiment.schemas import ExperimentStatus, ExperimentType, AssetType

class ExperimentSettingsModel(Base):
    __tablename__ = "experiment_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apply_setting: Mapped[ApplySetting] = mapped_column(Enum(ApplySetting))
    apply_on_percentile: Mapped[ApplyOnPercentile] = mapped_column(Enum(ApplyOnPercentile))
    apply_min_installs_variants: Mapped[int] = mapped_column(Integer)
    apply_min_installs_experiment: Mapped[int] = mapped_column(Integer)
    min_duration_days: Mapped[int] = mapped_column(Integer)
    max_duration_days: Mapped[int] = mapped_column(Integer)
    audience_skew: Mapped[Integer] = mapped_column(Integer)
    minimum_detectable_effect: Mapped[MinimumDetectableEffectEnum] = mapped_column(Enum(MinimumDetectableEffectEnum))
    confidence_interval: Mapped[ConfidenceIntervalEnum] = mapped_column(Enum(ConfidenceIntervalEnum))
    target_metric: Mapped[TargetMetric] = mapped_column(Enum(TargetMetric))
    early_kill_min_installs: Mapped[int] = mapped_column(Integer)
    early_kill_cvr_decrease: Mapped[float] = mapped_column(Float)
    kill_performance_value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    experiments: Mapped[List["ExperimentModel"]] = relationship(back_populates="settings")

class ExperimentModel(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settings_id: Mapped[int] = mapped_column(ForeignKey("experiment_settings.id"))
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"))
    csl_id: Mapped[str] = mapped_column(String(255))
    locale_id: Mapped[str] = mapped_column(String(10), nullable=True)
    # internal_experiment_id is the id of the experiment in the app with auto increment

    internal_experiment_id= mapped_column(Integer)
    experiment_title: Mapped[str] = mapped_column(String(255))
    hypothesis: Mapped[str] = mapped_column(String(1000), nullable=True)
    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus), default=ExperimentStatus.NOT_READY)
    error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    priority: Mapped[int] = mapped_column(Integer)

    
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    experiment_type: Mapped[ExperimentType] = mapped_column(Enum(ExperimentType))
    google_play_experiment_id: Mapped[str] = mapped_column(Integer, nullable=True)
    experiment_name_auto_populated: Mapped[str] = mapped_column(String(255))
    
    
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    app = relationship("AppModel", back_populates="experiments")
    settings = relationship("ExperimentSettingsModel", back_populates="experiments")
    variants: Mapped[List["VariantModel"]] = relationship("VariantModel", back_populates="experiment", cascade="all, delete-orphan")
  
class VariantModel(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
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
    
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    experiment = relationship("ExperimentModel", back_populates="variants")
  