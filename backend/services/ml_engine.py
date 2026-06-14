"""
ML Engine: CTR / CVR prediction with multi-tier fallback.

Priority: DeepFM (PyTorch) → XGBoost → Statistical baselines.
Each tier requires progressively fewer dependencies.
"""

from __future__ import annotations

import json
import random as _random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False

from backend.config import get_settings

settings = get_settings()


@dataclass
class PredictionResult:
    ctr: float          # predicted click-through rate (0-100%)
    cvr: float          # predicted conversion rate (0-100%)
    confidence: float   # model confidence (0-1)
    model_used: str     # "deepfm" | "xgboost" | "statistical"


class MLEngine:
    """CTR/CVR prediction engine.

    Usage:
        engine = MLEngine()
        pred = engine.predict(
            campaign_id=1,
            ad_group_id=3,
            age_range=[18, 34],
            gender="female",
            device="mobile",
            platform="simulated",
            hour=14,
        )
    """

    FEATURE_NAMES = [
        "hour", "day_of_week", "campaign_ctr", "campaign_cvr",
        "age_18_24", "age_25_34", "age_35_44", "age_45_plus",
        "gender_male", "gender_female",
        "device_mobile", "device_desktop", "device_tablet",
        "platform_simulated", "platform_google", "platform_meta", "platform_tiktok",
    ]

    def __init__(self) -> None:
        self._model: Optional[object] = None       # XGBoost model
        self._deepfm: Optional[object] = None      # DeepFM model
        self._deepfm_available = self._check_deepfm()
        self._model_path = settings.project_root / "data" / "ctr_model.json"
        self._deepfm_path = settings.project_root / "data" / "deepfm_model.pkl"

    @staticmethod
    def _check_deepfm() -> bool:
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------
    def predict(
        self,
        *,
        campaign_id: int,
        ad_group_id: int,
        age_range: Optional[list[int]] = None,
        gender: Optional[str] = None,
        device: str = "mobile",
        platform: str = "simulated",
        hour: Optional[int] = None,
        campaign_ctr: Optional[float] = None,
        campaign_cvr: Optional[float] = None,
    ) -> PredictionResult:
        """Predict CTR and CVR for a given ad placement context."""
        now = datetime.now(timezone.utc)
        h = hour if hour is not None else now.hour
        dow = now.weekday()

        # Build feature vector
        features = self._build_features(
            hour=h, dow=dow,
            age_range=age_range or [18, 65],
            gender=gender or "all",
            device=device,
            platform=platform,
            campaign_ctr=campaign_ctr or 3.5,
            campaign_cvr=campaign_cvr or 4.0,
        )

        # Try DeepFM first (highest accuracy)
        if self._deepfm is not None:
            try:
                fm_features = self._build_deepfm_features(
                    hour=h, dow=dow,
                    age_range=age_range or [18, 65],
                    gender=gender or "all",
                    device=device, platform=platform,
                    campaign_ctr=campaign_ctr or 3.5,
                    campaign_cvr=campaign_cvr or 4.0,
                )
                ctr_raw = float(self._deepfm.predict_single(fm_features))
                cvr_raw = ctr_raw * 1.2  # CVR ≈ CTR * 1.2 (typical ratio)
                return PredictionResult(
                    ctr=round(float(np.clip(ctr_raw * 100, 0.5, 15)), 3),
                    cvr=round(float(np.clip(cvr_raw * 100, 0.5, 20)), 3),
                    confidence=0.88,
                    model_used="deepfm",
                )
            except Exception:
                pass  # fall through to XGBoost

        # Try XGBoost
        if self._model is not None:
            try:
                arr = np.array([features], dtype=np.float32)
                ctr_raw, cvr_raw = self._model.predict(arr)[0]
                return PredictionResult(
                    ctr=round(float(np.clip(ctr_raw, 0.5, 15)), 3),
                    cvr=round(float(np.clip(cvr_raw, 0.5, 20)), 3),
                    confidence=0.85,
                    model_used="xgboost",
                )
            except Exception:
                pass  # fall through to statistical

        return self._statistical_predict(h, dow, features)

    def train(self, samples: list[dict]) -> None:
        """Train XGBoost model from a list of sample dicts.

        Each sample must have all keys from FEATURE_NAMES plus 'ctr' and 'cvr'.
        Returns True if training succeeded, False if insufficient data.
        """
        if len(samples) < 500:
            return  # not enough data

        try:
            import xgboost as xgb

            X = np.array([
                [s.get(f, 0) for f in self.FEATURE_NAMES]
                for s in samples
            ], dtype=np.float32)
            y_ctr = np.array([s["ctr"] for s in samples], dtype=np.float32)
            y_cvr = np.array([s["cvr"] for s in samples], dtype=np.float32)
            y = np.column_stack([y_ctr, y_cvr])

            self._model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective="reg:squarederror",
                random_state=42,
            )
            self._model.fit(X, y)

            # Persist
            self._model_path.parent.mkdir(parents=True, exist_ok=True)
            self._model.save_model(str(self._model_path))

        except ImportError:
            pass  # XGBoost not installed

    def load_model(self) -> bool:
        """Load a previously trained model from disk."""
        # Try DeepFM first
        if self._deepfm_path.exists():
            try:
                from backend.services.deepfm_model import DeepFMTrainer
                self._deepfm = DeepFMTrainer.load(str(self._deepfm_path))
                return True
            except Exception:
                pass

        # Fall back to XGBoost
        if not self._model_path.exists():
            return False
        try:
            import xgboost as xgb
            self._model = xgb.XGBRegressor()
            self._model.load_model(str(self._model_path))
            return True
        except Exception:
            return False

    # ----------------------------------------------------------------
    # DeepFM helpers
    # ----------------------------------------------------------------
    def _build_deepfm_features(
        self,
        hour: int, dow: int,
        age_range: list[int], gender: str,
        device: str, platform: str,
        campaign_ctr: float, campaign_cvr: float,
    ) -> dict:
        """Build a feature dict for DeepFM predict_single()."""
        age_min = min(age_range)
        age_max = max(age_range)
        daily_budget_ratio = 0.5  # placeholder

        return {
            "bid_strategy": 0,   # default
            "device_type": {"mobile": 0, "desktop": 1, "tablet": 2}.get(device, 0),
            "platform": {"simulated": 0, "google": 1, "meta": 2, "tiktok": 3}.get(platform, 0),
            "gender": {"male": 0, "female": 1, "all": 2}.get(gender, 2),
            "hour_of_day": hour,
            "day_of_week": dow,
            "daily_budget": 5000.0,
            "budget_spent_today": 2500.0,
            "budget_remaining_ratio": 0.5,
            "target_cpa": 50.0,
            "target_roas": 3.0,
            "max_cpc": 5.0,
            "age_min": float(age_min),
            "age_max": float(age_max),
            "campaign_ctr_historical": campaign_ctr,
            "campaign_cvr_historical": campaign_cvr,
            "quality_score": 6.0,
        }

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------
    def _build_features(
        self,
        hour: int,
        dow: int,
        age_range: list[int],
        gender: str,
        device: str,
        platform: str,
        campaign_ctr: float,
        campaign_cvr: float,
    ) -> list[float]:
        """Build the 17-element feature vector."""
        return [
            float(hour),
            float(dow),
            float(campaign_ctr),
            float(campaign_cvr),
            1.0 if 18 <= min(age_range) <= 24 else 0.0,
            1.0 if 25 <= min(age_range) <= 34 else 0.0,
            1.0 if 35 <= min(age_range) <= 44 else 0.0,
            1.0 if max(age_range) >= 45 else 0.0,
            1.0 if gender == "male" else 0.0,
            1.0 if gender == "female" else 0.0,
            1.0 if device == "mobile" else 0.0,
            1.0 if device == "desktop" else 0.0,
            1.0 if device == "tablet" else 0.0,
            1.0 if platform == "simulated" else 0.0,
            1.0 if platform == "google" else 0.0,
            1.0 if platform == "meta" else 0.0,
            1.0 if platform == "tiktok" else 0.0,
        ]

    def _statistical_predict(
        self, hour: int, _dow: int, _features: list[float]
    ) -> PredictionResult:
        """Statistical baseline when model is unavailable."""
        # Time-of-day adjustment (peak hours 10-12, 19-22)
        hour_factor = self._hour_multiplier(hour)
        base_ctr = 3.5 * hour_factor
        base_cvr = 4.5 * hour_factor

        return PredictionResult(
            ctr=round(base_ctr + _random.gauss(0, 0.3), 3),
            cvr=round(base_cvr + _random.gauss(0, 0.4), 3),
            confidence=0.55,
            model_used="statistical",
        )

    @staticmethod
    def _hour_multiplier(hour: int) -> float:
        """Return a multiplier for the given hour (0-23)."""
        if 10 <= hour <= 12:
            return 1.3
        if 19 <= hour <= 22:
            return 1.4
        if 0 <= hour <= 5:
            return 0.4
        return 1.0


# Singleton
_ml_engine: Optional[MLEngine] = None


def get_ml_engine() -> MLEngine:
    global _ml_engine
    if _ml_engine is None:
        _ml_engine = MLEngine()
        _ml_engine.load_model()
    return _ml_engine
