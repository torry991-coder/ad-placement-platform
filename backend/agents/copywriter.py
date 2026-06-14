"""CreativeAgent — generate ad creative copy (headlines, descriptions, CTAs).

Uses LLM if available; falls back to industry-specific template generation.
Considers campaign industry, existing creatives, and performance data.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.ad_group import AdGroup
from backend.models.creative import Creative
from backend.models.performance import PerformanceMetric
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


# ---------------------------------------------------------------------------
# Template library — used when no LLM is available
# ---------------------------------------------------------------------------

TEMPLATES = {
    "ecommerce": {
        "headlines": [
            "🔥 限时特惠 | {product} 低至5折",
            "新品首发 | {product} 抢先体验",
            "今日特卖 | {product} 买一送一",
            "会员专享 | {product} 额外9折",
            "热卖爆款 | {product} 万人好评",
        ],
        "descriptions": [
            "精选优质{product}，限时优惠中。现货速发，30天无忧退换。",
            "{product}新品上市，限时尝鲜价。品质保证，不满意全额退款。",
            "爆款{product}今日特惠，手慢无！全场满199包邮，快来抢购。",
            "品质{product}会员折扣中，叠加优惠券更划算。",
            "热销{product}，已售10万+件。真实用户好评，放心购买。",
        ],
        "ctas": [
            "立即抢购", "限时购买", "马上入手",
            "查看详情", "立即下单", "去购买",
        ],
    },
    "finance": {
        "headlines": [
            "稳健理财 | 年化收益高达{rate}%",
            "新用户专享 | 首投加息{rate}%",
            "智能投顾 | 让{rate}%收益触手可及",
            "安全可靠 | 银行级风控保障",
            "灵活存取 | 随时赎回零费用",
        ],
        "descriptions": [
            "专业团队管理，历史年化收益{rate}%。资金银行存管，安全有保障。",
            "新用户注册即享{rate}%加息券，1元起投，收益每日可见。",
            "AI智能投资组合，根据风险偏好自动配置。历史回报率{rate}%，低波动稳健增值。",
            "多重风控体系，资金全程监管。灵活存取，收益稳健，适合各类投资者。",
        ],
        "ctas": [
            "立即开户", "了解详情", "开始投资",
            "注册领取", "查看收益", "免费体验",
        ],
    },
    "education": {
        "headlines": [
            "限时免费 | {course}体验课开放中",
            "名师授课 | {course}从入门到精通",
            "就业保障 | {course}学完推荐就业",
            "AI时代必修 | {course}提升竞争力",
            "零基础也能学 | {course}速成班",
        ],
        "descriptions": [
            "资深讲师授课，{course}系统化学习路径。配套实战项目，学完可获证书，推荐就业。",
            "限时0元体验{course}，名师直播+录播任意学。已有10万+学员毕业，好评率98%。",
            "从零开始学{course}，AI辅助教学，个性化学习计划。学不会免费重学，保障学习效果。",
            "行业大咖亲授{course}，实战项目驱动，3个月掌握核心技能。学员就业率95%+。",
        ],
        "ctas": [
            "免费试听", "立即报名", "了解课程",
            "领取资料", "开始学习", "查看详情",
        ],
    },
    "default": {
        "headlines": [
            "品质之选 | {product}值得信赖",
            "限时优惠 | {product}惊喜价",
            "全新升级 | {product}体验更佳",
            "热门推荐 | {product}好评如潮",
            "专业品质 | {product}行业标杆",
        ],
        "descriptions": [
            "{product}全新升级，品质更优，性价比更高。限时优惠中，不要错过。",
            "选择{product}，就是选择品质和信赖。专业服务，满意保障。",
            "{product}热销中，真实用户好评。限时特惠，立即了解详情。",
            "热门{product}推荐，品质保证，售后无忧。快来体验吧。",
        ],
        "ctas": [
            "了解更多", "立即咨询", "查看详情",
            "马上体验", "立即购买", "联系我们",
        ],
    },
}

# Keyword → industry mapping
INDUSTRY_KEYWORDS = {
    "ecommerce": ["购物", "电商", "零售", "shop", "store", "buy", "购买", "商品", "折扣", "促销"],
    "finance": ["金融", "理财", "投资", "基金", "保险", "贷款", "bank", "invest", "收益", "利率"],
    "education": ["教育", "课程", "学习", "培训", "考试", "edu", "学校", "学员", "教学", "就业"],
}


class CreativeAgent:
    """Agent that generates ad creative copy."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def generate(
        self, campaign_id: int, db: AsyncSession, count: int = 3
    ) -> list[dict[str, Any]]:
        """Generate creative variations for the campaign.

        Returns:
            list of {headline, description, cta, industry, source} dicts.
        """
        try:
            campaign = await self._get_campaign(campaign_id, db)
            if campaign is None:
                return self._error_creatives(campaign_id, count, "Campaign not found")

            # Detect industry from campaign context
            industry = self._detect_industry(campaign)
            product = campaign.name or "产品"

            # Gather existing creatives for context
            existing_creatives = await self._get_existing_creatives(campaign_id, db)
            best_performers = await self._get_best_performing_creatives(campaign_id, db)

            context = {
                "campaign_name": campaign.name,
                "industry": industry,
                "product": product,
                "existing_creatives": existing_creatives[:5],
                "best_performers": best_performers[:3],
            }

            # Try LLM first
            if not isinstance(self.llm, FallbackProvider):
                try:
                    llm_result = await self._llm_generate(context, count)
                    if llm_result and len(llm_result) >= count:
                        return llm_result[:count]
                except Exception:
                    pass

            # Fallback: template-based generation
            return self._template_generate(context, count)

        except Exception as exc:
            return self._error_creatives(campaign_id, count, str(exc))

    # ── helpers ────────────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _get_existing_creatives(self, cid: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Fetch existing creatives for context."""
        result = await db.execute(
            select(Creative).join(AdGroup).where(AdGroup.campaign_id == cid).limit(20)
        )
        return [
            {
                "headline": c.headline,
                "description": c.description,
                "cta": c.call_to_action,
                "ctr": c.ctr or 0.0,
                "cvr": c.cvr or 0.0,
            }
            for c in result.scalars().all()
        ]

    async def _get_best_performing_creatives(
        self, cid: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get top creatives by CTR."""
        result = await db.execute(
            select(Creative)
            .join(AdGroup)
            .where(and_(AdGroup.campaign_id == cid, Creative.ctr > 0))
            .order_by(Creative.ctr.desc())
            .limit(5)
        )
        return [
            {
                "headline": c.headline,
                "description": c.description,
                "cta": c.call_to_action,
                "ctr": round(c.ctr or 0.0, 4),
                "impressions": c.impressions or 0,
            }
            for c in result.scalars().all()
        ]

    def _detect_industry(self, campaign: Campaign) -> str:
        """Detect industry from campaign name, labels, or notes."""
        text = f"{campaign.name or ''} {campaign.notes or ''} {' '.join(campaign.labels or [])}"
        text_lower = text.lower()
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                return industry
        return "default"

    # ── template-based generation ──────────────────────────────────────

    def _template_generate(self, context: dict[str, Any], count: int) -> list[dict[str, Any]]:
        """Generate creatives from templates with randomization and context injection."""
        industry = context.get("industry", "default")
        product = context.get("product", "产品")
        best = context.get("best_performers", [])

        templates = TEMPLATES.get(industry, TEMPLATES["default"])

        # If we have a best performer, use its CTA style
        best_cta = None
        if best:
            best_cta = best[0].get("cta")

        # Try to infer a "rate" or numeric placeholder for finance
        rate_val = "5.8"
        if industry == "finance":
            rate_val = f"{random.uniform(4.5, 8.0):.1f}"

        creatives = []
        seen = set()

        for i in range(count):
            attempts = 0
            while attempts < 20:
                headline_tpl = random.choice(templates["headlines"])
                desc_tpl = random.choice(templates["descriptions"])
                cta = best_cta if best_cta and i == 0 else random.choice(templates["ctas"])

                headline = headline_tpl.format(product=product, rate=rate_val, course=product)
                description = desc_tpl.format(product=product, rate=rate_val, course=product)

                key = (headline, description)
                if key not in seen:
                    seen.add(key)
                    break
                attempts += 1

            creatives.append({
                "headline": headline,
                "description": description,
                "cta": cta,
                "industry": industry,
                "source": "template",
            })

        return creatives

    # ── LLM generation ─────────────────────────────────────────────────

    async def _llm_generate(self, context: dict[str, Any], count: int) -> list[dict[str, Any]] | None:
        """Generate creatives via LLM."""
        prompt = f"""You are an expert advertising copywriter. Generate {count} ad creative variations for an advertising campaign.

Campaign: {context['campaign_name']}
Industry: {context['industry']}
Product/Service: {context['product']}

Existing creatives for context:
{json.dumps(context.get('existing_creatives', []), indent=2, ensure_ascii=False)}

Best performing creatives:
{json.dumps(context.get('best_performers', []), indent=2, ensure_ascii=False)}

Requirements:
- Each creative must have a headline (under 90 chars), description (under 180 chars), and CTA.
- Use the industry context to create relevant, compelling copy.
- Include Chinese text if the market is Chinese.
- Avoid duplicating existing creatives.
- Make CTAs action-oriented and specific.

Return ONLY a JSON array of objects with keys "headline", "description", "cta". No markdown fences, no additional text."""
        try:
            reply = await self.llm.chat(prompt)
            if "[" in reply and "]" in reply:
                start = reply.index("[")
                end = reply.rindex("]") + 1
                creatives = json.loads(reply[start:end])
                for c in creatives:
                    c["source"] = "llm"
                    c["industry"] = context.get("industry", "unknown")
                return creatives
        except Exception:
            pass
        return None

    @staticmethod
    def _error_creatives(campaign_id: int, count: int, error: str) -> list[dict[str, Any]]:
        return [{
            "headline": f"Campaign #{campaign_id} - 品质之选",
            "description": f"品质保障，值得信赖。（生成出错：{error}）",
            "cta": "了解更多",
            "industry": "default",
            "source": "fallback_error",
        }] * max(count, 1)
