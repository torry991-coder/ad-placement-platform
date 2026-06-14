"""A/B experiment engine with Bayesian & frequentist statistical tests.

Uses scipy.stats for t-test when available, otherwise falls back to a manual
Welch's t-test implementation. Bayesian posterior probability computed via
a Beta-binomial conjugate model (conversion rate).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import random as _random
import math

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.experiment import Experiment
from backend.models.performance import PerformanceMetric
from backend.models.enums import ExperimentStatus

# ── optional scipy ─────────────────────────────────────────────────────
try:
    from scipy import stats as scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ── manual Welch t-test (fallback) ─────────────────────────────────────
def _welch_ttest(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Manual Welch's t-test (unequal variances).

    Returns (t_statistic, p_value_two_sided, degrees_of_freedom).
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return (0.0, 1.0, 0.0)

    m1, m2 = sum(a) / n1, sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)

    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return (0.0, 1.0, 0.0)

    t_stat = (m1 - m2) / se

    num = (v1 / n1 + v2 / n2) ** 2
    denom = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = num / denom if denom > 0 else 1.0

    p_val = _students_t_survival(abs(t_stat), df) * 2.0
    p_val = min(p_val, 1.0)
    return (t_stat, p_val, df)


def _students_t_survival(x: float, df: float) -> float:
    """Survival function (1 - CDF) for Student's t-distribution."""
    if df <= 0:
        return 0.5
    a = df / 2.0
    b = 0.5
    z = df / (df + x * x)
    ib = _regularized_beta(z, a, b)
    return 0.5 * ib


def _regularized_beta(x: float, a: float, b: float, max_iter: int = 200) -> float:
    """Regularised incomplete beta I_x(a,b) via Lentz's continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - log_beta) / a

    fpm = 1.0
    c_val = 1.0
    d_val = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d_val) < 1e-30:
        d_val = 1e-30
    d_val = 1.0 / d_val
    f_val = d_val

    for m in range(1, max_iter + 1):
        mm2 = 2 * m
        num = m * (b - m) * x / ((a + mm2 - 1) * (a + mm2))
        d_val = 1.0 + num * d_val
        if abs(d_val) < 1e-30:
            d_val = 1e-30
        c_val = 1.0 + num / c_val
        if abs(c_val) < 1e-30:
            c_val = 1e-30
        d_val = 1.0 / d_val
        f_val *= c_val * d_val

        num = -(a + m) * (a + b + m) * x / ((a + mm2) * (a + mm2 + 1))
        d_val = 1.0 + num * d_val
        if abs(d_val) < 1e-30:
            d_val = 1e-30
        c_val = 1.0 + num / c_val
        if abs(c_val) < 1e-30:
            c_val = 1e-30
        d_val = 1.0 / d_val
        delta = c_val * d_val
        f_val *= delta

        if abs(delta - 1.0) < 3e-7:
            break

    return front * (f_val - 1.0)


# ── Bayesian Beta-binomial posterior probability ───────────────────────
def _bayesian_prob(
    control_successes: float,
    control_trials: float,
    variant_successes: float,
    variant_trials: float,
    prior_a: float = 1.0,
    prior_b: float = 1.0,
    n_samples: int = 100_000,
) -> float:
    """Probability that variant > control using Beta-binomial model."""
    alpha_c = prior_a + control_successes
    beta_c = prior_b + control_trials - control_successes
    alpha_v = prior_a + variant_successes
    beta_v = prior_b + variant_trials - variant_successes

    if alpha_c <= 0 or beta_c <= 0 or alpha_v <= 0 or beta_v <= 0:
        return 0.5

    if not _HAS_NUMPY:
        # Fallback: simple heuristic based on conversion rate comparison
        ctrl_rate = control_successes / control_trials if control_trials > 0 else 0
        var_rate = variant_successes / variant_trials if variant_trials > 0 else 0
        if var_rate > ctrl_rate:
            return 0.6 + (var_rate - ctrl_rate) * 0.3
        return 0.5

    samples_c = np.random.beta(alpha_c, beta_c, size=n_samples)
    samples_v = np.random.beta(alpha_v, beta_v, size=n_samples)

    prob = float((samples_v > samples_c).mean())
    return prob


# ── confidence interval ─────────────────────────────────────────────────
def _confidence_interval(data: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Compute confidence interval for a mean via normal approximation."""
    n = len(data)
    if n < 2:
        mean = sum(data) / n if n > 0 else 0.0
        return (mean, mean)

    mean = sum(data) / n
    se = (sum((x - mean) ** 2 for x in data) / (n - 1)) ** 0.5 / math.sqrt(n)

    if _HAS_SCIPY:
        z = scipy_stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0)
    else:
        z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_map.get(confidence, 1.96)

    return (mean - z * se, mean + z * se)


# ── public API ──────────────────────────────────────────────────────────
async def run_analysis(experiment_id: int, db: AsyncSession) -> dict[str, Any]:
    """Run full A/B analysis on an experiment.

    Fetches performance metrics for control and variant campaigns, computes
    frequentist t-test and Bayesian posterior probability, and updates the
    Experiment row with results.

    Returns:
        Dict with: experiment_id, p_value, confidence_level, is_significant,
        winner_variant, bayesian_prob, control_metrics, variant_metrics,
        sample_sizes, uplift_pct, confidence_interval_lower/upper.
    """
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None:
        return {"error": f"Experiment {experiment_id} not found"}

    control_id = experiment.control_campaign_id
    variant_id = experiment.variant_campaign_id

    metrics_ctrl = await _fetch_metric_values(control_id, db)
    metrics_var = await _fetch_metric_values(variant_id, db)

    if not metrics_ctrl or not metrics_var:
        return {
            "experiment_id": experiment_id,
            "error": "Insufficient data for analysis",
            "control_rows": len(metrics_ctrl),
            "variant_rows": len(metrics_var),
        }

    ctrl_conversions = sum(m.get("conversions", 0) for m in metrics_ctrl)
    ctrl_clicks = sum(m.get("clicks", 0) for m in metrics_ctrl)
    ctrl_impressions = sum(m.get("impressions", 0) for m in metrics_ctrl)
    ctrl_spend = sum(m.get("spend", 0.0) for m in metrics_ctrl)
    ctrl_revenue = sum(m.get("revenue", 0.0) for m in metrics_ctrl)

    var_conversions = sum(m.get("conversions", 0) for m in metrics_var)
    var_clicks = sum(m.get("clicks", 0) for m in metrics_var)
    var_impressions = sum(m.get("impressions", 0) for m in metrics_var)
    var_spend = sum(m.get("spend", 0.0) for m in metrics_var)
    var_revenue = sum(m.get("revenue", 0.0) for m in metrics_var)

    def _safe_rate(num: float, den: float) -> float:
        return round(num / den * 100.0, 4) if den > 0 else 0.0

    def _safe_ratio(num: float, den: float) -> float:
        return round(num / den, 4) if den > 0 else 0.0

    control_metrics = {
        "impressions": ctrl_impressions,
        "clicks": ctrl_clicks,
        "conversions": ctrl_conversions,
        "spend": round(ctrl_spend, 2),
        "revenue": round(ctrl_revenue, 2),
        "ctr": _safe_rate(ctrl_clicks, ctrl_impressions),
        "cvr": _safe_rate(ctrl_conversions, ctrl_clicks),
        "cpa": round(ctrl_spend / ctrl_conversions, 4) if ctrl_conversions > 0 else 0.0,
        "roas": _safe_ratio(ctrl_revenue, ctrl_spend),
    }
    variant_metrics = {
        "impressions": var_impressions,
        "clicks": var_clicks,
        "conversions": var_conversions,
        "spend": round(var_spend, 2),
        "revenue": round(var_revenue, 2),
        "ctr": _safe_rate(var_clicks, var_impressions),
        "cvr": _safe_rate(var_conversions, var_clicks),
        "cpa": round(var_spend / var_conversions, 4) if var_conversions > 0 else 0.0,
        "roas": _safe_ratio(var_revenue, var_spend),
    }

    ctrl_rates = [
        (m.get("conversions", 0) / m.get("clicks", 1)) * 100.0
        if m.get("clicks", 0) > 0 else 0.0
        for m in metrics_ctrl
    ]
    var_rates = [
        (m.get("conversions", 0) / m.get("clicks", 1)) * 100.0
        if m.get("clicks", 0) > 0 else 0.0
        for m in metrics_var
    ]

    if _HAS_SCIPY:
        t_result = scipy_stats.ttest_ind(var_rates, ctrl_rates, equal_var=False)
        t_stat = float(t_result.statistic)
        p_value = float(t_result.pvalue)
    else:
        t_stat, p_value, _ = _welch_ttest(var_rates, ctrl_rates)

    confidence_level = round((1.0 - p_value) * 100.0, 2) if p_value < 1.0 else 0.0
    is_significant = p_value < 0.05

    bayesian_prob = _bayesian_prob(
        control_successes=float(ctrl_conversions),
        control_trials=float(ctrl_clicks) if ctrl_clicks > 0 else 1.0,
        variant_successes=float(var_conversions),
        variant_trials=float(var_clicks) if var_clicks > 0 else 1.0,
    )

    var_cvr = variant_metrics["cvr"]
    ctrl_cvr = control_metrics["cvr"]
    if is_significant:
        winner_variant = "variant" if var_cvr > ctrl_cvr else "control"
    else:
        winner_variant = "inconclusive"

    if ctrl_cvr > 0:
        uplift_pct = round((var_cvr - ctrl_cvr) / ctrl_cvr * 100.0, 2)
    else:
        uplift_pct = 0.0

    diff_rates = [v - c for v, c in zip(var_rates, ctrl_rates)]
    ci_lower, ci_upper = _confidence_interval(diff_rates, confidence=0.95)

    result_dict = {
        "experiment_id": experiment_id,
        "experiment_name": experiment.name,
        "p_value": round(p_value, 6),
        "confidence_level": confidence_level,
        "is_significant": is_significant,
        "winner_variant": winner_variant,
        "bayesian_prob": round(bayesian_prob, 4),
        "t_statistic": round(t_stat, 4),
        "uplift_pct": uplift_pct,
        "confidence_interval": [round(ci_lower, 4), round(ci_upper, 4)],
        "control_metrics": control_metrics,
        "variant_metrics": variant_metrics,
        "sample_sizes": {
            "control_intervals": len(metrics_ctrl),
            "variant_intervals": len(metrics_var),
        },
    }

    experiment.results = result_dict
    experiment.is_significant = is_significant
    experiment.confidence_level = confidence_level
    experiment.winner_variant = winner_variant

    if experiment.auto_stop and is_significant:
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.now(timezone.utc)

    await db.flush()
    return result_dict


# ── helpers ─────────────────────────────────────────────────────────────
async def _fetch_metric_values(
    campaign_id: int, db: AsyncSession
) -> list[dict[str, Any]]:
    """Fetch per-interval performance rows for a campaign."""
    result = await db.execute(
        select(PerformanceMetric).where(
            and_(
                PerformanceMetric.campaign_id == campaign_id,
                PerformanceMetric.clicks > 0,
            )
        ).order_by(PerformanceMetric.date.asc(), PerformanceMetric.hour.asc())
    )
    rows = result.scalars().all()

    return [
        {
            "impressions": r.impressions or 0,
            "clicks": r.clicks or 0,
            "conversions": r.conversions or 0,
            "spend": float(r.spend or 0),
            "revenue": float(r.revenue or 0),
        }
        for r in rows
    ]


# ── CRUD & lifecycle ────────────────────────────────────────────────────
async def list_experiments(
    db: AsyncSession,
    status: ExperimentStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Experiment], int]:
    """List experiments, optionally filtered by status, newest first."""
    stmt_base = select(Experiment)
    count_stmt = select(func.count(Experiment.id))

    if status is not None:
        stmt_base = stmt_base.where(Experiment.status == status)
        count_stmt = count_stmt.where(Experiment.status == status)

    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar() or 0

    stmt = stmt_base.order_by(Experiment.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    experiments = list(result.scalars().all())

    return experiments, total


async def create_experiment(db: AsyncSession, data: dict[str, Any]) -> Experiment:
    """Create a new Experiment ORM instance from a data dict."""
    experiment = Experiment(**data)
    db.add(experiment)
    await db.flush()
    await db.refresh(experiment)
    return experiment


async def get_experiment(
    db: AsyncSession, experiment_id: int
) -> Experiment | None:
    """Get a single experiment by ID, or None."""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    return result.scalar_one_or_none()


async def update_experiment(
    db: AsyncSession, experiment: Experiment, data: dict[str, Any]
) -> Experiment:
    """Update experiment fields from a data dict, skipping None values."""
    for key, value in data.items():
        if value is not None:
            setattr(experiment, key, value)
    await db.flush()
    await db.refresh(experiment)
    return experiment


async def start_experiment(
    db: AsyncSession, experiment: Experiment
) -> Experiment:
    """Start an experiment: set status to RUNNING and start_date if not set."""
    experiment.status = ExperimentStatus.RUNNING
    if experiment.start_date is None:
        experiment.start_date = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(experiment)
    return experiment


async def stop_experiment(
    db: AsyncSession, experiment: Experiment
) -> Experiment:
    """Stop an experiment: set status to STOPPED and end_date to now."""
    experiment.status = ExperimentStatus.STOPPED
    experiment.end_date = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(experiment)
    return experiment


async def get_experiment_results(
    db: AsyncSession, experiment: Experiment
) -> dict[str, Any]:
    """Get analysis results for an experiment, delegating to run_analysis."""
    result = await run_analysis(experiment.id, db)
    result["name"] = experiment.name
    result["status"] = experiment.status.value
    return result
