from datetime import date
from enum import Enum

from pydantic import BaseModel


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class PoiVisitSummary(BaseModel):
    poi_id: str
    name: str
    visits: int


class LanguageVisitSummary(BaseModel):
    language: str
    visits: int


class DailyVisitSummary(BaseModel):
    date: date
    visits: int


class AnalyticsResponse(BaseModel):
    start_date: date
    end_date: date
    total_visits: int
    by_poi: list[PoiVisitSummary]
    by_language: list[LanguageVisitSummary]
    by_day: list[DailyVisitSummary]
