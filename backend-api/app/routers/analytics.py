from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from app.authz import require_permission
from app.database import ReportExport, Visit, get_database
from app.schemas.analytics import (
    AnalyticsResponse,
    ExportFormat,
    HourlyVisitorResponse,
    WeeklyVisitorResponse,
)
from app.services.analytics import AnalyticsService


def create_analytics_router() -> APIRouter:
    router = APIRouter(prefix="/admin/reports", tags=["admin analytics"])
    analytics_service = AnalyticsService()

    @router.get("", response_model=AnalyticsResponse)
    async def get_analytics(
        start_date: date,
        end_date: date,
        database: Any = Depends(get_database),
        _: dict[str, Any] = Depends(require_permission("analytics:read")),
    ) -> AnalyticsResponse:
        return AnalyticsResponse(**await analytics_service.summarize(database, start_date, end_date))

    @router.get("/visitor-count")
    async def get_visitor_count(
        start: datetime,
        end: datetime,
        database: Any = Depends(get_database),
        _: dict[str, Any] = Depends(require_permission("visitor:read")),
    ) -> dict[str, int]:
        return {
            "total_visits": await analytics_service.count_visitor_connections(database, start, end),
        }

    @router.get("/weekly-visitors", response_model=WeeklyVisitorResponse)
    async def get_weekly_visitors(
        database: Any = Depends(get_database),
        _: dict[str, Any] = Depends(require_permission("visitor:read")),
    ) -> WeeklyVisitorResponse:
        return WeeklyVisitorResponse(**await analytics_service.weekly_visitor_counts(database))

    @router.get("/hourly-visitors", response_model=HourlyVisitorResponse)
    async def get_hourly_visitors(
        database: Any = Depends(get_database),
        _: dict[str, Any] = Depends(require_permission("visitor:read")),
    ) -> HourlyVisitorResponse:
        return HourlyVisitorResponse(**await analytics_service.hourly_visitor_counts(database))

    @router.get(
        "/export",
        response_class=Response,
        responses={
            200: {
                "description": "Report file",
                "content": {
                    "text/csv": {"schema": {"type": "string", "format": "binary"}},
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                        "schema": {"type": "string", "format": "binary"}
                    },
                    "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                },
            }
        },
    )
    async def export_analytics(
        start_date: date,
        end_date: date,
        format: ExportFormat = Query(),
        database: Any = Depends(get_database),
        admin: dict[str, Any] = Depends(require_permission("analytics:read")),
    ) -> Response:
        report = AnalyticsResponse(**await analytics_service.summarize(database, start_date, end_date))
        data, media_type, extension = analytics_service.export(report, format)
        database.add(
            ReportExport(
                admin_id=admin["_id"],
                start_date=start_date,
                end_date=end_date,
                format=format.value,
            )
        )
        await database.commit()
        filename = f"tourist-visits-{start_date.isoformat()}-{end_date.isoformat()}.{extension}"
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router


router = create_analytics_router()
