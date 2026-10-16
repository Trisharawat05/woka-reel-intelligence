from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.instagram import InstagramAccount
from app.models.analytics import CreatorAnalytics
from app.schemas.analytics import AnalyticsResponse, AnalyticsSummary, AnalyticsTimeSeriesPoint, DemographicsData, TopPostItem

def get_analytics_dashboard(db: Session, workspace_id: str) -> AnalyticsResponse:
    account = db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == workspace_id,
        InstagramAccount.is_connected == True
    ).first()

    followers_base = account.followers_count if account else 34200
    is_sandbox = account.is_sandbox if account else True
    media_count = account.media_count if account else 118

    # Generate 30-day time series points
    today = date.today()
    time_series: List[AnalyticsTimeSeriesPoint] = []
    
    current_followers = followers_base
    growth_rate = 32  # avg daily follower gain
    
    for i in range(30, -1, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.strftime("%b %d")
        # Slight realistic variance
        var_factor = ((i * 7) % 19) - 8
        followers_at_day = current_followers - ((i) * growth_rate) + var_factor
        reach_at_day = int(followers_at_day * 0.42 + (i % 5) * 850)
        impressions_at_day = int(reach_at_day * 1.65)
        er_at_day = round(3.8 + ((i % 4) * 0.3) - 0.1, 2)

        time_series.append(AnalyticsTimeSeriesPoint(
            date=day_str,
            followers=max(followers_at_day, 100),
            reach=reach_at_day,
            impressions=impressions_at_day,
            engagement_rate=er_at_day
        ))

    summary = AnalyticsSummary(
        followers_count=followers_base,
        followers_growth_30d=int(growth_rate * 30),
        following_count=485,
        media_count=media_count,
        reach_30d=int(followers_base * 3.4),
        impressions_30d=int(followers_base * 5.8),
        avg_engagement_rate=4.25,
        is_sandbox=is_sandbox
    )

    demographics = DemographicsData(
        age_distribution={
            "18-24": 34.0,
            "25-34": 46.5,
            "35-44": 14.2,
            "45+": 5.3
        },
        gender_distribution={
            "Women": 58.2,
            "Men": 39.5,
            "Non-binary": 2.3
        },
        top_countries={
            "United States": 42.1,
            "United Kingdom": 18.4,
            "Canada": 12.0,
            "Germany": 8.5,
            "Australia": 6.8
        },
        top_cities={
            "New York": 14.2,
            "London": 11.5,
            "Los Angeles": 9.8,
            "Toronto": 6.4,
            "Berlin": 4.5
        }
    )

    top_posts: List[TopPostItem] = [
        TopPostItem(
            id="post_top_1",
            media_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=80",
            permalink="https://instagram.com/p/Cxyz123",
            caption="3 secret tools every creator needs in 2026 to automate their community growth 🔥 Comment 'TOOLS' below!",
            like_count=4280,
            comments_count=892,
            reach=38500,
            engagement_rate=6.4,
            published_at="3 days ago"
        ),
        TopPostItem(
            id="post_top_2",
            media_url="https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=500&auto=format&fit=crop&q=80",
            permalink="https://instagram.com/p/Cxyz124",
            caption="How I negotiated a $5,000 brand sponsorship with 30k followers. Full rate card breakdown in bio 💼",
            like_count=3120,
            comments_count=415,
            reach=29400,
            engagement_rate=5.1,
            published_at="1 week ago"
        ),
        TopPostItem(
            id="post_top_3",
            media_url="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=500&auto=format&fit=crop&q=80",
            permalink="https://instagram.com/p/Cxyz125",
            caption="Desk setup refresh! Which mechanical keyboard switch do you swear by? Drop your thoughts 👇",
            like_count=2890,
            comments_count=320,
            reach=24100,
            engagement_rate=4.7,
            published_at="2 weeks ago"
        )
    ]

    return AnalyticsResponse(
        summary=summary,
        time_series=time_series,
        demographics=demographics,
        top_posts=top_posts
    )
