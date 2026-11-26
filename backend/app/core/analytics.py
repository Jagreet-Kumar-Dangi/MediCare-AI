from enum import Enum

REPORTING_TIMEZONE = "Asia/Kolkata"


class AnalyticsPeriod(str, Enum):
    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    PREVIOUS_MONTH = "previous_month"
    CUSTOM = "custom"


class TrendGranularity(str, Enum):
    DAILY = "day"
    WEEKLY = "week"
    MONTHLY = "month"
