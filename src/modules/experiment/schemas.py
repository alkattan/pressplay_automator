from enum import Enum

class ExperimentType(Enum):
    AI = "AI"
    SCREENSHOT_ORDER = "Screenshot Order"
    MANUAL = "Manual"
    REPLICATION = "Replication"

class ExperimentStatus(Enum):
    READY = "ready"
    NOT_READY = "not_ready"
    ERROR = "error"
    IN_PROGRESS = "in_progress"
    STOPPING = "stopping"
    FINISHED = "finished"

class AssetType(Enum):
    MULTI_ASSET = "MU"
    PROMO_VIDEO = "PV"
    SHORT_DESCRIPTION = "SD"
    FULL_DESCRIPTION = "FD"
    SCREEN_SHOTS = "SS"
    ICON = "IC"
    FEATURE_GRAPHIC = "FG"

class ApplySetting(Enum):
    WIN = "win"
    ON_PERCENTILE = "on_percentile"
    NEVER = "never"

class ApplyOnPercentile(Enum):
    PERCENTILE_50 = 50
    PERCENTILE_55 = 55
    PERCENTILE_60 = 60
    PERCENTILE_65 = 65
    PERCENTILE_70 = 70
    PERCENTILE_75 = 75
    PERCENTILE_80 = 80
    PERCENTILE_85 = 85
    PERCENTILE_90 = 90
    PERCENTILE_95 = 95
    PERCENTILE_100 = 100

# class AudienceSkewEnum(Enum):
#     DEFAULT = "default"
#     SKEW_10 = 10
#     SKEW_20 = 20
#     SKEW_30 = 30
#     SKEW_40 = 40
#     SKEW_50 = 50
#     SKEW_60 = 60
#     SKEW_70 = 70
#     SKEW_80 = 80

class MinimumDetectableEffectEnum(Enum):
    EFFECT_0_5 = 0.5
    EFFECT_1_0 = 1.0
    EFFECT_1_5 = 1.5
    EFFECT_2_0 = 2.0
    EFFECT_2_5 = 2.5
    EFFECT_3_0 = 3.0 
    EFFECT_4_0 = 4.0 
    EFFECT_5_0 = 5.0 
    EFFECT_6_0 = 6.0

class ConfidenceIntervalEnum(Enum):
    CI_90 = 90
    CI_95 = 95
    CI_98 = 98
    CI_99 = 99

class TargetMetric(Enum):
    FIRST_TIME_INSTALLERS = "First-time installers"
    RETAINED_FIRST_TIME_INSTALLERS = "Retained first-time installers (recommended)"
    RETAINED_PRE_REGISTRATIONS="Retained pre-registrations"