"""Reports REST API — generate and export performance reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    ReportGenerateRequest,
    ReportResponse,
)
from backend.services import report_generator

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a performance report with the specified parameters.

    Report data can be exported as CSV or PDF via the export endpoints.
    """
    try:
        data = await report_generator.generate_report(
            db,
            report_type=body.report_type,
            campaign_id=body.campaign_id,
            date_from=body.date_from,
            date_to=body.date_to,
            metrics=body.metrics,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Report generation failed: {exc}",
        )

    return ReportResponse(
        report_id=data["report_id"],
        report_type=data["report_type"],
        generated_at=data["generated_at"],
        data=data,
    )


@router.get("/export/csv")
async def export_csv(
    report_type: str = Query("daily"),
    campaign_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export report data as CSV file."""
    try:
        data = await report_generator.generate_report(
            db,
            report_type=report_type,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"CSV export failed: {exc}",
        )

    csv_content = report_generator.export_csv(data)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ad_report_{data['report_id']}.csv"
        },
    )


@router.get("/export/pdf")
async def export_pdf(
    report_type: str = Query("daily"),
    campaign_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export report data as PDF file (HTML-based simple PDF)."""
    try:
        data = await report_generator.generate_report(
            db,
            report_type=report_type,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"PDF export failed: {exc}",
        )

    pdf_content = report_generator.export_pdf(data)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ad_report_{data['report_id']}.pdf"
        },
    )


@router.get("/export/xlsx")
async def export_xlsx(
    report_type: str = Query("daily"),
    campaign_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export report data as a multi-sheet Excel (.xlsx) file."""
    try:
        data = await report_generator.generate_report(
            db,
            report_type=report_type,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Excel export failed: {exc}",
        )

    xlsx_bytes = report_generator.export_excel(data)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=ad_report_{data['report_id']}.xlsx"
        },
    )
