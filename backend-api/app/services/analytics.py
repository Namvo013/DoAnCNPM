import csv
import io
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import POI, Visit
from app.schemas.analytics import AnalyticsResponse, ExportFormat


class AnalyticsService:
    async def count_visitor_connections(
        self,
        database: AsyncSession,
        start: datetime,
        end: datetime,
    ) -> int:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start and end must be timezone-aware and end must be later than start",
            )
        count = await database.scalar(
            select(func.count())
            .select_from(Visit)
            .where(
                Visit.event_type == "visitor_connect",
                Visit.created_at >= start,
                Visit.created_at < end,
            )
        )
        return int(count or 0)

    async def summarize(
        self,
        database: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_date must not be earlier than start_date",
            )
        start = datetime.combine(start_date, time.min, timezone.utc)
        end = datetime.combine(end_date + timedelta(days=1), time.min, timezone.utc)
        conditions = (
            Visit.event_type == "poi_enter",
            Visit.created_at >= start,
            Visit.created_at < end,
        )
        total = await database.scalar(
            select(func.count()).select_from(Visit).where(*conditions)
        )
        total = int(total or 0)
        if total == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No visit data for this date range")

        poi_rows = (
            await database.execute(
                select(Visit.poi_id, func.count().label("visits"))
                .where(*conditions)
                .group_by(Visit.poi_id)
                .order_by(func.count().desc(), Visit.poi_id.asc())
            )
        ).all()
        language_rows = (
            await database.execute(
                select(Visit.language, func.count().label("visits"))
                .where(*conditions)
                .group_by(Visit.language)
                .order_by(func.count().desc(), Visit.language.asc())
            )
        ).all()
        timestamps = await database.scalars(
            select(Visit.created_at).where(*conditions).order_by(Visit.created_at)
        )
        daily_counts: dict[date, int] = {}
        for timestamp in timestamps:
            day = timestamp.date()
            daily_counts[day] = daily_counts.get(day, 0) + 1
        poi_ids = [poi_id for poi_id, _ in poi_rows if poi_id is not None]
        pois = await database.execute(select(POI.id, POI.name).where(POI.id.in_(poi_ids))) if poi_ids else None
        poi_names = {poi_id: name for poi_id, name in pois.all()} if pois is not None else {}
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_visits": total,
            "by_poi": [
                {
                    "poi_id": poi_id or "",
                    "name": poi_names.get(poi_id, poi_id or "unknown"),
                    "visits": visits,
                }
                for poi_id, visits in poi_rows
            ],
            "by_language": [
                {"language": language or "unknown", "visits": visits}
                for language, visits in language_rows
            ],
            "by_day": [
                {"date": day, "visits": visits}
                for day, visits in sorted(daily_counts.items())
            ],
        }

    @staticmethod
    def export(report: AnalyticsResponse, export_format: ExportFormat) -> tuple[bytes, str, str]:
        if export_format is ExportFormat.CSV:
            return AnalyticsService._csv(report), "text/csv; charset=utf-8", "csv"
        if export_format is ExportFormat.XLSX:
            return (
                AnalyticsService._xlsx(report),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            )
        return AnalyticsService._pdf(report), "application/pdf", "pdf"

    @staticmethod
    def _csv(report: AnalyticsResponse) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Start date", report.start_date.isoformat()])
        writer.writerow(["End date", report.end_date.isoformat()])
        writer.writerow(["Total visits", report.total_visits])
        writer.writerow([])
        writer.writerow(["By POI", "POI ID", "Name", "Visits"])
        writer.writerows(
            ["POI", item.poi_id, item.name, item.visits] for item in report.by_poi
        )
        writer.writerow([])
        writer.writerow(["By language", "Language", "Visits"])
        writer.writerows(["Language", item.language, item.visits] for item in report.by_language)
        writer.writerow([])
        writer.writerow(["By day", "Date", "Visits"])
        writer.writerows(["Day", item.date.isoformat(), item.visits] for item in report.by_day)
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def _xlsx(report: AnalyticsResponse) -> bytes:
        workbook = Workbook()
        summary = workbook.active
        summary.title = "Summary"
        summary.append(["Metric", "Value"])
        summary.append(["Start date", report.start_date.isoformat()])
        summary.append(["End date", report.end_date.isoformat()])
        summary.append(["Total visits", report.total_visits])
        sheets = (
            ("By POI", ["POI ID", "Name", "Visits"], [[item.poi_id, item.name, item.visits] for item in report.by_poi]),
            ("By language", ["Language", "Visits"], [[item.language, item.visits] for item in report.by_language]),
            ("By day", ["Date", "Visits"], [[item.date.isoformat(), item.visits] for item in report.by_day]),
        )
        for title, headers, rows in sheets:
            sheet = workbook.create_sheet(title)
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
        for sheet in workbook.worksheets:
            for cell in sheet[1]:
                cell.font = Font(bold=True)
            sheet.freeze_panes = "A2"
            for column in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in column)
                sheet.column_dimensions[column[0].column_letter].width = min(width + 2, 60)
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    @staticmethod
    def _pdf(report: AnalyticsResponse) -> bytes:
        output = io.BytesIO()
        document = SimpleDocTemplate(output, pagesize=letter, title="Tourist visit report")
        styles = getSampleStyleSheet()
        content: list[Any] = [
            Paragraph("Tourist visit report", styles["Title"]),
            Paragraph(
                f"Period: {report.start_date.isoformat()} to {report.end_date.isoformat()}",
                styles["Normal"],
            ),
            Paragraph(f"Total visits: {report.total_visits}", styles["Normal"]),
            Spacer(1, 12),
        ]
        tables = (
            (
                "Visits by POI",
                [["POI ID", "Visits"]] + [[item.poi_id, str(item.visits)] for item in report.by_poi],
            ),
            (
                "Visits by language",
                [["Language", "Visits"]] + [[item.language, str(item.visits)] for item in report.by_language],
            ),
            (
                "Visits by day",
                [["Date", "Visits"]] + [[item.date.isoformat(), str(item.visits)] for item in report.by_day],
            ),
        )
        for title, rows in tables:
            content.extend(
                [
                    Paragraph(title, styles["Heading2"]),
                    Table(
                        rows,
                        repeatRows=1,
                        style=TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]
                        ),
                    ),
                    Spacer(1, 12),
                ]
            )
        document.build(content)
        return output.getvalue()
