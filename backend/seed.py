"""Seed sample data for development/demo."""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.ad_group import AdGroup
from backend.models.creative import Creative
from backend.models.performance import PerformanceMetric
from backend.models.enums import (
    BidStrategy,
    CampaignStatus,
    AdGroupStatus,
)

PLATFORMS = [["simulated"], ["simulated", "google"], ["simulated", "meta", "tiktok"]]
INDUSTRIES = ["电商", "游戏", "金融", "教育", "医疗", "本地生活"]
AGE_RANGES = [[18, 24], [25, 34], [35, 44], [18, 65]]
DEVICES = [["mobile"], ["desktop"], ["mobile", "desktop", "tablet"]]
REGIONS = [["CN"], ["US"], ["CN", "US", "JP"], ["北京", "上海", "广州", "深圳"]]


async def seed_data(db: AsyncSession, num_campaigns: int = 12) -> None:
    """Insert sample campaigns, ad groups, creatives, and performance data."""
    now = datetime.now(timezone.utc)

    for i in range(1, num_campaigns + 1):
        c = Campaign(
            name=f"{random.choice(INDUSTRIES)}-活动{i}",
            status=random.choice(list(CampaignStatus)),
            daily_budget=random.uniform(500, 20000),
            total_budget=random.uniform(5000, 200000),
            bid_strategy=random.choice(list(BidStrategy)),
            target_cpa=random.uniform(10, 200) if random.random() > 0.3 else None,
            target_roas=random.uniform(1.5, 8.0) if random.random() > 0.3 else None,
            max_cpc=random.uniform(0.5, 10.0),
            start_date=now - timedelta(days=random.randint(0, 60)),
            end_date=now + timedelta(days=random.randint(10, 90)),
            platforms=random.choice(PLATFORMS),
            created_at=now - timedelta(days=random.randint(1, 60)),
            updated_at=now,
        )
        db.add(c)
        await db.flush()

        # 2-4 ad groups per campaign
        for j in range(random.randint(2, 4)):
            ag = AdGroup(
                campaign_id=c.id,
                name=f"广告组-{chr(65+j)}",
                status=AdGroupStatus.ACTIVE if c.status == CampaignStatus.ACTIVE else AdGroupStatus.PAUSED,
                max_cpc=random.uniform(0.5, 8.0),
                target_cpa=c.target_cpa,
                age_range=random.choice(AGE_RANGES),
                gender=random.choice(["male", "female", "all"]),
                devices=random.choice(DEVICES),
                regions=random.choice(REGIONS),
                keywords=random.sample(
                    ["促销", "折扣", "新品", "限时", "特价", "满减", "秒杀", "包邮", "首发", "旗舰"],
                    k=random.randint(2, 5),
                ),
                created_at=now - timedelta(days=random.randint(1, 30)),
                updated_at=now,
            )
            db.add(ag)
            await db.flush()

            # 1-3 creatives per ad group
            for k in range(random.randint(1, 3)):
                imp = random.randint(1000, 500000)
                clk = int(imp * random.uniform(0.01, 0.08))
                conv = int(clk * random.uniform(0.02, 0.12))
                cr = Creative(
                    ad_group_id=ag.id,
                    name=f"创意素材-{k+1}",
                    creative_type=random.choice(["text", "image", "responsive"]),
                    headline=random.choice([
                        "限时特惠，全场5折起",
                        "新品首发，抢先体验",
                        "品质之选，值得信赖",
                        "百万用户的选择",
                    ]),
                    description=random.choice([
                        "现在下单立享优惠，满300减50",
                        "品质保证，7天无理由退换",
                        "专业团队为您服务，24小时在线",
                    ]),
                    call_to_action=random.choice(["立即购买", "了解更多", "免费试用", "限时抢购"]),
                    impressions=imp,
                    clicks=clk,
                    conversions=conv,
                    ctr=round((clk / imp) * 100, 2) if imp > 0 else 0,
                    cvr=round((conv / clk) * 100, 2) if clk > 0 else 0,
                    fatigue_score=round(random.uniform(0, 80), 1),
                    is_active=True,
                    created_at=now - timedelta(days=random.randint(0, 20)),
                    updated_at=now,
                )
                db.add(cr)

        # Performance data (last 7 days)
        for d in range(7):
            date = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            for h in range(24) if d < 3 else [None]:  # hourly for recent 3 days, daily for older
                imp = random.randint(500, 50000) if h is not None else random.randint(12000, 500000)
                clk = int(imp * random.uniform(0.01, 0.06))
                conv = int(clk * random.uniform(0.02, 0.10))
                spend = random.uniform(imp * 0.0001, imp * 0.005)
                revenue = spend * random.uniform(1.0, 5.0)

                pm = PerformanceMetric(
                    campaign_id=c.id,
                    date=date,
                    hour=h,
                    platform="simulated",
                    impressions=imp,
                    clicks=clk,
                    conversions=conv,
                    spend=round(spend, 2),
                    revenue=round(revenue, 2),
                    ctr=round((clk / imp) * 100, 3) if imp > 0 else 0,
                    cvr=round((conv / clk) * 100, 3) if clk > 0 else 0,
                    cpc=round(spend / clk, 3) if clk > 0 else 0,
                    cpa=round(spend / conv, 3) if conv > 0 else 0,
                    roas=round(revenue / spend, 2) if spend > 0 else 0,
                    quality_score=round(random.uniform(3, 10), 1),
                    bounce_rate=round(random.uniform(20, 70), 1),
                )
                db.add(pm)

    await db.flush()


async def _run_seed() -> None:
    """Entry point: initialise DB and seed data."""
    from backend.database import init_db, async_session_factory

    await init_db()
    async with async_session_factory() as db:
        await seed_data(db, num_campaigns=12)
        print("Seed data inserted successfully (12 campaigns with performance data).")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_run_seed())
