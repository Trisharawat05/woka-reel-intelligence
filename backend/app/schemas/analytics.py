from typing import List, Dict, Any
from pydantic import BaseModel

class TopPostItem(BaseModel):
    id: str
    media_url: str
    permalink: str
    caption: str
    like_count: int
    comments_count: int
    reach: int
    engagement_rate: float
    published_at: str

class AnalyticsTimeSeriesPoint(BaseModel):
    date: str
    followers: int
    reach: int
    impressions: int
    engagement_rate: float

class AnalyticsSummary(BaseModel):
    followers_count: int
    followers_growth_30d: int
    following_count: int
    media_count: int
    reach_30d: int
    impressions_30d: int
    avg_engagement_rate: float
    is_sandbox: bool

class DemographicsData(BaseModel):
    age_distribution: Dict[str, float]
    gender_distribution: Dict[str, float]
    top_countries: Dict[str, float]
    top_cities: Dict[str, float]

class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    time_series: List[AnalyticsTimeSeriesPoint]
    demographics: DemographicsData
    top_posts: List[TopPostItem]
