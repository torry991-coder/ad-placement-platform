"""Experiments REST API — A/B test CRUD + lifecycle management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResultsResponse,
    ExperimentUpdate,
)
from backend.services import ab_testing

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("/", response_model=dict)
async def list_experiments(
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all experiments with optional status filter."""
    experiments, total = await ab_testing.list_experiments(
        db, status=status, offset=offset, limit=limit
    )
    return {
        "data": [ExperimentResponse.model_validate(e).model_dump() for e in experiments],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    body: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new A/B experiment."""
    data = body.model_dump()
    experiment = await ab_testing.create_experiment(db, data)
    return ExperimentResponse.model_validate(experiment)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single experiment by ID."""
    experiment = await ab_testing.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.model_validate(experiment)


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: int,
    body: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update experiment fields (name, traffic_split, end_date, hypothesis)."""
    experiment = await ab_testing.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    updated = await ab_testing.update_experiment(
        db, experiment, body.model_dump(exclude_unset=True)
    )
    return ExperimentResponse.model_validate(updated)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Start an experiment, changing status to RUNNING."""
    experiment = await ab_testing.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if hasattr(experiment.status, "value") and experiment.status.value != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start experiment in status: {experiment.status.value if hasattr(experiment.status, 'value') else experiment.status}",
        )
    updated = await ab_testing.start_experiment(db, experiment)
    return ExperimentResponse.model_validate(updated)


@router.post("/{experiment_id}/stop", response_model=ExperimentResponse)
async def stop_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Stop a running experiment."""
    experiment = await ab_testing.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if hasattr(experiment.status, "value") and experiment.status.value not in ("running",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop experiment in status: {experiment.status.value if hasattr(experiment.status, 'value') else experiment.status}",
        )
    updated = await ab_testing.stop_experiment(db, experiment)
    return ExperimentResponse.model_validate(updated)


@router.get("/{experiment_id}/results", response_model=ExperimentResultsResponse)
async def get_experiment_results(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get experiment results with statistical analysis."""
    experiment = await ab_testing.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    results = await ab_testing.get_experiment_results(db, experiment)
    return ExperimentResultsResponse(**results)
