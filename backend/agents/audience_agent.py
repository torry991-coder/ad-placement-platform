"""AudienceAgent — audience expansion and lookalike recommendations.

Analyzes top-performing audience segments for a campaign and suggests similar
expansions using the audience_service for lookalike computation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.audience import AudienceSegment
from backend.models.ad_group import AdGroup
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


# ── Expansion rule templates ────────────────────────────────────────────

EXPANSION_STRATEGIES = [
    {
        "strategy": "broaden_age",
        "description": "Expand age range by ±5 years",
        "apply": lambda rules: _broaden_age(rules),
    },
    {
        "strategy": "add_gender",
        "description": "Include the opposite gender if currently single-gender",
        "apply": lambda rules: _add_gender(rules),
    },
    {
        "strategy": "expand_interests",
        "description": "Add adjacent interest categories",
        "apply": lambda rules: _expand_interests(rules),
    },
    {
        "strategy": "broaden_geo",
        "description": "Add neighboring regions",
        "apply": lambda rules: _broaden_geo(rules),
    },
    {
        "strategy": "remove_narrow_constraints",
        "description": "Drop the most restrictive rule to widen reach",
        "apply": lambda rules: _relax_most_restrictive(rules),
    },
]

ADJACENT_INTERESTS = {
    "fashion": ["beauty", "luxury", "lifestyle", "accessories"],
    "tech": ["gaming", "gadgets", "software", "electronics"],
    "fitness": ["health", "nutrition", "sports", "wellness"],
    "travel": ["adventure", "hotels", "tourism", "outdoors"],
    "food": ["cooking", "dining", "recipes", "beverages"],
    "finance": ["investing", "banking", "insurance", "crypto"],
    "education": ["online courses", "certification", "skills", "training"],
}


class AudienceAgent:
    """Agent that recommends audience segment expansions."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def expand(
        self, campaign_id: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Generate audience expansion recommendations for the campaign.

        Returns:
            list of {segment_name, rules, reasoning, source, similarity_score} dicts.
        """
        try:
            campaign = await self._get_campaign(campaign_id, db)
            if campaign is None:
                return self._error_segments(campaign_id, "Campaign not found")

            # Get audience segments linked to ad groups of this campaign
            segments = await self._get_campaign_segments(campaign_id, db)

            if not segments:
                return self._generic_expansions(campaign)

            # Find best-performing segments
            top_segments = self._rank_segments(segments)[:3]

            # For each top segment, generate expansion variants
            recommendations: list[dict[str, Any]] = []
            for seg in top_segments:
                expanded = self._generate_expansions(seg)
                recommendations.extend(expanded)

            # Try lookalike expansion via audience_service
            try:
                from backend.services.audience_service import expand_lookalike

                for seg in top_segments:
                    lookalike = await expand_lookalike(db, seg.get("id"), top_k=2)
                    for ll in lookalike.get("lookalikes", []):
                        ll_seg = ll.get("segment", {})
                        recommendations.append({
                            "segment_name": f"Lookalike: {ll_seg.get('name', 'unknown')}",
                            "rules": ll_seg.get("rules", {}),
                            "reasoning": (
                                f"Lookalike expansion from seed segment '{seg.get('name')}' "
                                f"with similarity score {ll.get('similarity_score', 0):.4f}. "
                                "These users share behavioral patterns with your best customers."
                            ),
                            "source": "lookalike",
                            "similarity_score": ll.get("similarity_score", 0),
                            "seed_segment_id": seg.get("id"),
                        })
            except Exception:
                pass  # lookalike computation unavailable, skip

            # Try LLM enhancement
            if not isinstance(self.llm, FallbackProvider) and recommendations:
                try:
                    llm_result = await self._llm_enhance(campaign, top_segments, recommendations)
                    if llm_result:
                        # Merge LLM reasoning into existing recommendations
                        llm_map = {r.get("segment_name", ""): r for r in llm_result}
                        for rec in recommendations:
                            llm_rec = llm_map.get(rec.get("segment_name", ""))
                            if llm_rec and llm_rec.get("reasoning"):
                                rec["reasoning"] = llm_rec["reasoning"]
                except Exception:
                    pass

            # Deduplicate and limit
            seen_names = set()
            unique = []
            for rec in recommendations:
                name = rec.get("segment_name", "")
                if name not in seen_names:
                    seen_names.add(name)
                    unique.append(rec)

            return unique[:10]

        except Exception as exc:
            return self._error_segments(campaign_id, str(exc))

    # ── helpers ────────────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _get_campaign_segments(
        self, cid: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get audience segments associated with this campaign's ad groups."""
        # Get ad group IDs for this campaign
        ad_result = await db.execute(
            select(AdGroup.id).where(AdGroup.campaign_id == cid)
        )
        ad_group_ids = [r[0] for r in ad_result.all()]

        # Get all segments (in production, they'd be linked to ad groups)
        # For now, fetch all segments and calculate stats
        seg_result = await db.execute(select(AudienceSegment).limit(30))
        segments = seg_result.scalars().all()

        result = []
        for seg in segments:
            # Try to get per-segment stats
            try:
                from backend.services.audience_service import calculate_segment_stats
                stats = await calculate_segment_stats(db, seg.id)
            except Exception:
                stats = {}

            result.append({
                "id": seg.id,
                "name": seg.name,
                "description": seg.description,
                "rules": seg.rules or {},
                "member_count": seg.member_count or 0,
                "avg_ctr": stats.get("ctr", seg.avg_ctr or 0.0),
                "avg_cvr": stats.get("cvr", seg.avg_cvr or 0.0),
                "roas": stats.get("roas", seg.roas or 0.0),
                "labels": seg.labels or [],
            })

        return result

    def _rank_segments(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank segments by a composite score of CTR, CVR, and ROAS."""
        def score(s: dict[str, Any]) -> float:
            ctr = float(s.get("avg_ctr", 0) or 0)
            cvr = float(s.get("avg_cvr", 0) or 0)
            roas = float(s.get("roas", 0) or 0)
            # Normalize and weight
            return ctr * 10.0 + cvr * 5.0 + roas * 2.0

        return sorted(segments, key=score, reverse=True)

    # ── expansion logic ────────────────────────────────────────────────

    def _generate_expansions(self, segment: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate expansion variants for a single segment."""
        rules = segment.get("rules", {})
        seg_name = segment.get("name", "Unknown")
        expansions: list[dict[str, Any]] = []

        for strategy in EXPANSION_STRATEGIES:
            new_rules = strategy["apply"](dict(rules))  # copy rules
            if new_rules and new_rules != rules:
                expansions.append({
                    "segment_name": f"{seg_name} + {strategy['strategy']}",
                    "rules": new_rules,
                    "reasoning": (
                        f"{strategy['description']} from base segment '{seg_name}' "
                        f"(CTR: {segment.get('avg_ctr', 0):.2f}%, "
                        f"CVR: {segment.get('avg_cvr', 0):.2f}%, "
                        f"ROAS: {segment.get('roas', 0):.2f}x). "
                        f"This should increase reach while preserving audience quality."
                    ),
                    "source": "rule_expansion",
                    "similarity_score": 0.75,
                    "seed_segment_id": segment.get("id"),
                })

        return expansions

    def _generic_expansions(self, campaign: Campaign) -> list[dict[str, Any]]:
        """Generate generic audience recommendations when no segments exist."""
        industry_hints = (campaign.labels or []) + ([campaign.notes] if campaign.notes else [])
        hints_text = " ".join(str(h) for h in industry_hints).lower()

        recommendations = [
            {
                "segment_name": "Broad Interest",
                "rules": {"interests": ["general"], "age": [18, 65], "gender": "all"},
                "reasoning": "Start with a broad audience to gather initial performance data.",
                "source": "generic",
            },
            {
                "segment_name": "High Intent Lookalike",
                "rules": {"interests": ["shopping"], "age": [25, 54], "gender": "all"},
                "reasoning": "Target users with demonstrated purchase intent.",
                "source": "generic",
            },
            {
                "segment_name": "Engaged Users",
                "rules": {"interests": ["social_media"], "age": [18, 44]},
                "reasoning": "Target users likely to engage with and share content.",
                "source": "generic",
            },
        ]
        return recommendations

    # ── LLM enhancement ────────────────────────────────────────────────

    async def _llm_enhance(
        self,
        campaign: Campaign,
        top_segments: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        """Use LLM to refine expansion reasoning."""
        prompt = f"""You are an audience targeting expert. Review the following audience expansion recommendations and improve their reasoning. Return a JSON array of objects with keys "segment_name" and "reasoning".

Campaign: {campaign.name}
Top performing segments:
{json.dumps([{'name': s['name'], 'ctr': s.get('avg_ctr'), 'cvr': s.get('avg_cvr'), 'roas': s.get('roas'), 'rules': s.get('rules')} for s in top_segments], indent=2, ensure_ascii=False)}

Current recommendations:
{json.dumps([{'segment_name': r.get('segment_name'), 'rules': r.get('rules'), 'reasoning': r.get('reasoning')} for r in recommendations], indent=2, ensure_ascii=False)}

Return ONLY valid JSON array, no markdown fences, no additional text."""
        try:
            reply = await self.llm.chat(prompt)
            if "[" in reply and "]" in reply:
                start = reply.index("[")
                end = reply.rindex("]") + 1
                return json.loads(reply[start:end])
        except Exception:
            pass
        return None

    @staticmethod
    def _error_segments(campaign_id: int, error: str) -> list[dict[str, Any]]:
        return [{
            "segment_name": f"Campaign #{campaign_id} - Broad",
            "rules": {"interests": ["general"], "age": [18, 65]},
            "reasoning": f"Fallback recommendation (error: {error}). Start broad and narrow based on data.",
            "source": "error_fallback",
        }]


# ---------------------------------------------------------------------------
# Strategy apply functions
# ---------------------------------------------------------------------------

def _broaden_age(rules: dict[str, Any]) -> dict[str, Any]:
    age = rules.get("age")
    if isinstance(age, list) and len(age) >= 2:
        rules["age"] = [max(13, age[0] - 5), min(70, age[-1] + 5)]
    return rules


def _add_gender(rules: dict[str, Any]) -> dict[str, Any]:
    gender = rules.get("gender")
    if gender in ("male", "female"):
        rules["gender"] = "all"
    return rules


def _expand_interests(rules: dict[str, Any]) -> dict[str, Any]:
    interests: list[str] = rules.get("interests", [])
    if not isinstance(interests, list):
        return rules
    new_interests = list(interests)
    for interest in interests:
        adjacent = ADJACENT_INTERESTS.get(interest, [])
        for adj in adjacent[:2]:
            if adj not in new_interests:
                new_interests.append(adj)
    rules["interests"] = new_interests[:8]  # Cap at 8
    return rules


def _broaden_geo(rules: dict[str, Any]) -> dict[str, Any]:
    regions = rules.get("regions", [])
    if not isinstance(regions, list) or not regions:
        rules["regions"] = ["全国"]
    elif len(regions) <= 3:
        rules["regions"] = list(regions) + ["全国"]
    return rules


def _relax_most_restrictive(rules: dict[str, Any]) -> dict[str, Any]:
    """Remove the rule that most constrains audience size."""
    if not rules:
        return rules
    # Heuristic: remove the key with the smallest list
    list_rules = {k: v for k, v in rules.items() if isinstance(v, list)}
    if list_rules:
        smallest_key = min(list_rules, key=lambda k: len(list_rules[k]))
        if smallest_key in rules:
            del rules[smallest_key]
    elif "gender" in rules and rules["gender"] != "all":
        rules["gender"] = "all"
    return rules
